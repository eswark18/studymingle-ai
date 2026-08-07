from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentSession, CurrentUser, DatabaseSession
from app.core.config import settings
from app.core.security import create_session_token, hash_password, verify_password
from app.core.turnstile import verify_turnstile
from app.models import Session, User
from app.schemas.auth import DeleteAccountRequest, LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 60 * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


async def issue_session(database: DatabaseSession, user: User, response: Response) -> None:
    token = create_session_token()
    database.add(
        Session(
            user_id=user.id,
            token_hash=token.hashed,
            expires_at=datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours),
        )
    )
    await database.commit()
    set_session_cookie(response, token.raw)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    database: DatabaseSession,
) -> User:
    await verify_turnstile(payload.turnstile_token, request)
    normalized_email = payload.email.lower()
    existing = await database.scalar(select(User.id).where(User.email == normalized_email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        education_track=payload.education_track,
        grade_or_year=payload.grade_or_year,
    )
    database.add(user)
    try:
        await database.flush()
        await issue_session(database, user, response)
    except IntegrityError as exc:
        await database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
        ) from exc
    await database.refresh(user)
    return user


@router.post("/login", response_model=UserResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    database: DatabaseSession,
) -> User:
    await verify_turnstile(payload.turnstile_token, request)
    user = await database.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or user.deleted_at is not None or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    await issue_session(database, user, response)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    database: DatabaseSession,
    auth_session: CurrentSession,
) -> None:
    auth_session.revoked_at = datetime.now(UTC)
    await database.commit()
    clear_session_cookie(response)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> User:
    return user


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    database: DatabaseSession,
    user: CurrentUser,
) -> None:
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password is incorrect.")
    user.deleted_at = datetime.now(UTC)
    user.email = f"deleted-{user.id}@deleted.invalid"
    user.display_name = None
    user.education_track = None
    user.grade_or_year = None
    await database.execute(
        update(Session)
        .where(Session.user_id == user.id)
        .where(Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await database.commit()
    clear_session_cookie(response)
