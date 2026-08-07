import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.worksheets import owned_worksheet
from app.core.ocr_jobs import process_ocr_job
from app.models import ExtractedQuestion, OcrJob, Worksheet
from app.schemas.ocr import OcrJobResponse, QuestionResponse, QuestionUpdate

router = APIRouter(tags=["ocr"])


async def owned_job(
    job_id: uuid.UUID,
    user: CurrentUser,
    database: DatabaseSession,
) -> OcrJob:
    job = await database.scalar(
        select(OcrJob)
        .join(Worksheet)
        .where(OcrJob.id == job_id)
        .where(Worksheet.user_id == user.id)
        .where(Worksheet.deleted_at.is_(None))
        .options(selectinload(OcrJob.questions))
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found.")
    return job


@router.post(
    "/worksheets/{worksheet_id}/extract",
    response_model=OcrJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_extraction(
    worksheet_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    database: DatabaseSession,
) -> OcrJob:
    worksheet = await owned_worksheet(worksheet_id, user, database)
    active_job = await database.scalar(
        select(OcrJob)
        .where(OcrJob.worksheet_id == worksheet.id)
        .where(OcrJob.status.in_(["queued", "retrying", "processing"]))
    )
    if active_job is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This worksheet already has an active extraction job.",
        )

    job = OcrJob(worksheet_id=worksheet.id, status="queued", questions=[])
    worksheet.status = "queued"
    database.add(job)
    await database.commit()
    background_tasks.add_task(process_ocr_job, job.id)
    return await owned_job(job.id, user, database)


@router.get("/ocr-jobs/{job_id}", response_model=OcrJobResponse)
async def get_extraction(
    job_id: uuid.UUID,
    user: CurrentUser,
    database: DatabaseSession,
) -> OcrJob:
    return await owned_job(job_id, user, database)


@router.post("/ocr-jobs/{job_id}/retry", response_model=OcrJobResponse)
async def retry_extraction(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    database: DatabaseSession,
) -> OcrJob:
    job = await owned_job(job_id, user, database)
    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed extraction jobs can be retried.",
        )
    job.status = "retrying"
    job.error_message = None
    job.completed_at = None
    await database.commit()
    background_tasks.add_task(process_ocr_job, job.id)
    return await owned_job(job.id, user, database)


@router.patch("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    user: CurrentUser,
    database: DatabaseSession,
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
    question.edited_text = " ".join(payload.text.split())
    await database.commit()
    await database.refresh(question)
    return question
