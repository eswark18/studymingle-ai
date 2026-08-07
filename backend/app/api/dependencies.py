from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.security import hash_session_token
from app.models import Session, User

DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_session(
    database: DatabaseSession,
    session_cookie: Annotated[str | None, Cookie(alias=settings.session_cookie_name)] = None,
) -> Session:
    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    result = await database.execute(
        select(Session)
        .where(Session.token_hash == hash_session_token(session_cookie))
        .where(Session.revoked_at.is_(None))
        .where(Session.expires_at > datetime.now(UTC))
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    return session


CurrentSession = Annotated[Session, Depends(get_current_session)]


async def get_current_user(
    database: DatabaseSession,
    auth_session: CurrentSession,
) -> User:
    user = await database.get(User, auth_session.user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
