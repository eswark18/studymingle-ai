import asyncio
import time
import uuid
from collections import defaultdict, deque

from app.core.config import settings


class TutorRateLimiter:
    """Small single-process limiter; replace with Redis when the API scales horizontally."""

    def __init__(self) -> None:
        self._requests: dict[uuid.UUID, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, user_id: uuid.UUID) -> bool:
        now = time.monotonic()
        cutoff = now - settings.tutor_rate_limit_window_seconds
        async with self._lock:
            requests = self._requests[user_id]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= settings.tutor_rate_limit_requests:
                return False
            requests.append(now)
            return True


tutor_rate_limiter = TutorRateLimiter()
