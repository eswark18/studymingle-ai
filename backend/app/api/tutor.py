import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import settings
from app.core.rate_limit import tutor_rate_limiter
from app.core.tutor import (
    TutorContext,
    TutorProviderError,
    get_tutor_provider,
    requests_complete_solution,
)
from app.models import ExtractedQuestion, OcrJob, TutorAttempt, TutorHint, TutorSession, Worksheet
from app.schemas.tutor import (
    TutorAttemptRequest,
    TutorSessionResponse,
    TutorStartRequest,
)

router = APIRouter(tags=["tutor"])


async def _check_rate_limit(user: CurrentUser) -> None:
    if not await tutor_rate_limiter.allow(user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Tutor request limit reached. Please pause for a minute and try again.",
        )


async def _owned_question(
    question_id: uuid.UUID, user: CurrentUser, database: DatabaseSession
) -> ExtractedQuestion:
    question = await database.scalar(
        select(ExtractedQuestion)
        .join(OcrJob)
        .join(Worksheet)
        .where(ExtractedQuestion.id == question_id)
        .where(Worksheet.user_id == user.id)
        .where(Worksheet.deleted_at.is_(None))
    )
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    return question


async def _owned_session(
    session_id: uuid.UUID, user: CurrentUser, database: DatabaseSession
) -> TutorSession:
    session = await database.scalar(
        select(TutorSession)
        .where(TutorSession.id == session_id, TutorSession.user_id == user.id)
        .options(
            selectinload(TutorSession.question),
            selectinload(TutorSession.hints),
            selectinload(TutorSession.attempts),
        )
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tutor session not found."
        )
    return session


def _context(session: TutorSession, latest_attempt: str | None = None) -> TutorContext:
    question = session.question
    return TutorContext(
        source_text=question.extracted_text,
        learning_text=question.edited_text or question.extracted_text,
        education_track=session.education_track,
        grade_or_year=session.grade_or_year,
        subject=session.subject,
        prior_hints=tuple(hint.hint_text for hint in session.hints),
        prior_attempts=tuple(attempt.attempt_text for attempt in session.attempts),
        latest_attempt=latest_attempt,
    )


def _response(session: TutorSession) -> TutorSessionResponse:
    return TutorSessionResponse(
        id=session.id,
        question_id=session.question_id,
        source_text=session.question.extracted_text,
        learning_text=session.question.edited_text or session.question.extracted_text,
        education_track=session.education_track,
        grade_or_year=session.grade_or_year,
        subject=session.subject,
        status=session.status,
        hints=session.hints,
        attempts=session.attempts,
        can_request_hint=(
            session.status == "active" and len(session.hints) < settings.tutor_max_hints
        ),
        created_at=session.created_at,
    )


async def _generate(context: TutorContext, purpose: str):
    try:
        return await get_tutor_provider().generate(context, purpose)
    except TutorProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.post(
    "/questions/{question_id}/tutor-sessions",
    response_model=TutorSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_tutor_session(
    question_id: uuid.UUID,
    payload: TutorStartRequest,
    user: CurrentUser,
    database: DatabaseSession,
) -> TutorSessionResponse:
    await _check_rate_limit(user)
    question = await _owned_question(question_id, user, database)
    initial_context = TutorContext(
        source_text=question.extracted_text,
        learning_text=question.edited_text or question.extracted_text,
        education_track=payload.education_track,
        grade_or_year=payload.grade_or_year,
        subject=payload.subject,
    )
    guidance = await _generate(initial_context, "start")

    session = TutorSession(
        user_id=user.id,
        question_id=question.id,
        education_track=payload.education_track,
        grade_or_year=" ".join(payload.grade_or_year.split()),
        subject=" ".join(payload.subject.split()),
        status="active",
    )
    session.hints.append(
        TutorHint(sequence_number=1, hint_type=guidance.hint_type, hint_text=guidance.message)
    )
    database.add(session)
    await database.commit()
    session = await _owned_session(session.id, user, database)
    return _response(session)


@router.get("/tutor-sessions/{session_id}", response_model=TutorSessionResponse)
async def get_tutor_session(
    session_id: uuid.UUID, user: CurrentUser, database: DatabaseSession
) -> TutorSessionResponse:
    return _response(await _owned_session(session_id, user, database))


@router.post("/tutor-sessions/{session_id}/hints", response_model=TutorSessionResponse)
async def request_tutor_hint(
    session_id: uuid.UUID, user: CurrentUser, database: DatabaseSession
) -> TutorSessionResponse:
    await _check_rate_limit(user)
    session = await _owned_session(session_id, user, database)
    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This session is complete."
        )
    if len(session.hints) >= settings.tutor_max_hints:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Try an answer before requesting more guidance.",
        )
    guidance = await _generate(_context(session), "next_hint")
    session.hints.append(
        TutorHint(
            sequence_number=len(session.hints) + 1,
            hint_type=guidance.hint_type,
            hint_text=guidance.message,
        )
    )
    await database.commit()
    return _response(await _owned_session(session.id, user, database))


@router.post("/tutor-sessions/{session_id}/attempts", response_model=TutorSessionResponse)
async def submit_tutor_attempt(
    session_id: uuid.UUID,
    payload: TutorAttemptRequest,
    user: CurrentUser,
    database: DatabaseSession,
) -> TutorSessionResponse:
    await _check_rate_limit(user)
    session = await _owned_session(session_id, user, database)
    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This session is complete."
        )
    attempt_text = " ".join(payload.attempt_text.split())
    purpose = "explain_solution" if requests_complete_solution(attempt_text) else "check_attempt"
    guidance = await _generate(_context(session, latest_attempt=attempt_text), purpose)
    session.attempts.append(
        TutorAttempt(
            attempt_text=attempt_text,
            feedback_text=guidance.message,
            misconception=guidance.misconception,
            is_correct=guidance.is_correct,
        )
    )
    if (
        purpose == "explain_solution"
        or guidance.is_correct is True
        or guidance.next_action == "complete"
    ):
        session.status = "completed"
    await database.commit()
    return _response(await _owned_session(session.id, user, database))
