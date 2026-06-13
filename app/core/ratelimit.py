from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.limiter import is_rate_limited


class RateLimiter:
    def __init__(self, times: int, seconds: int) -> None:
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        if settings.load_test:
            return
        ip = request.client.host if request.client else "unknown"
        key = f"rl:{request.method}:{request.url.path}:{ip}"
        if await is_rate_limited(key, self.times, self.seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
            )
        # Additional per-user rate limiting when bearer token is present
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                from app.core.security import decode_token
                payload = decode_token(token)
                user_id = payload.get("sub")
                if user_id:
                    user_key = f"rl:{request.method}:{request.url.path}:user:{user_id}"
                    if await is_rate_limited(user_key, self.times, self.seconds):
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many requests",
                        )
            except Exception:
                pass
