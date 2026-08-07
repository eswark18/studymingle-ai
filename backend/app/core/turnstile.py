import httpx
from fastapi import HTTPException, Request, status

from app.core.config import settings


async def verify_turnstile(token: str | None, request: Request) -> None:
    if not settings.turnstile_secret_key:
        if settings.app_env == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Human verification is not configured.",
            )
        return

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Human verification is required.",
        )

    payload = {
        "secret": settings.turnstile_secret_key,
        "response": token,
        "remoteip": request.headers.get("CF-Connecting-IP"),
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data=payload,
            )
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Human verification is temporarily unavailable.",
        ) from exc

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Human verification failed or expired.",
        )
