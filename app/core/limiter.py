from redis.asyncio import Redis

_redis: Redis | None = None


def set_redis(client: Redis) -> None:
    global _redis
    _redis = client


async def close_redis() -> None:
    if _redis:
        await _redis.aclose()


def get_redis() -> Redis:
    assert _redis is not None, "Redis not initialised"
    return _redis


async def is_rate_limited(key: str, times: int, seconds: int) -> bool:
    """Fixed-window counter. Returns True if the request should be blocked."""
    redis = get_redis()
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, seconds)
    return count > times
