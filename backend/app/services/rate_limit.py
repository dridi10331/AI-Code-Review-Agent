import time

from fastapi import HTTPException, status
from redis.asyncio import Redis


class RateLimiter:
    def __init__(self, redis_client: Redis, max_requests: int, window_seconds: int) -> None:
        self._redis = redis_client
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def enforce(self, user_id: str) -> dict[str, int]:
        window_bucket = int(time.time() // self._window_seconds)
        key = f"rate_limit:{user_id}:{window_bucket}"

        current = await self._redis.incr(key)
        if current == 1:
            await self._redis.expire(key, self._window_seconds)

        if current > self._max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Rate limit exceeded.",
                    "limit": self._max_requests,
                    "window_seconds": self._window_seconds,
                },
            )

        return {
            "remaining": max(0, self._max_requests - current),
            "limit": self._max_requests,
            "window_seconds": self._window_seconds,
        }
