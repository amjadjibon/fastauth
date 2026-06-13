import logging

from app.core.limiter import get_redis

logger = logging.getLogger("fastauth")

_KEY_PREFIX = "jti:blocked:"


async def block_token(jti: str, ttl_seconds: int) -> None:
    """Add a JTI to the Redis blocklist with automatic expiry. No-ops if Redis is unavailable."""
    redis = get_redis()
    if redis is None:
        return
    try:
        if ttl_seconds > 0:
            await redis.set(f"{_KEY_PREFIX}{jti}", "1", ex=ttl_seconds)  # ty: ignore[invalid-await]
    except Exception:
        logger.warning("token_blocklist: failed to block jti %s", jti)


async def is_blocked(jti: str) -> bool:
    """Return True if the JTI is on the blocklist. Fails open on Redis error."""
    redis = get_redis()
    if redis is None:
        return False
    try:
        return await redis.exists(f"{_KEY_PREFIX}{jti}") == 1  # ty: ignore[invalid-await]
    except Exception:
        logger.warning("token_blocklist: failed to check jti %s — failing open", jti)
        return False
