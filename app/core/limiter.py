import time
from collections import defaultdict

from redis.asyncio import Redis

_redis: Redis | None = None

# in-memory fallback: key -> (count, window_start)
_memory: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))


def set_redis(client: Redis) -> None:
    global _redis
    _redis = client


async def close_redis() -> None:
    if _redis:
        await _redis.aclose()


async def is_rate_limited(key: str, times: int, seconds: int) -> bool:
    if _redis is not None:
        return await _redis_limited(key, times, seconds)
    return _memory_limited(key, times, seconds)


async def _redis_limited(key: str, times: int, seconds: int) -> bool:
    assert _redis is not None
    count = await _redis.incr(key)
    if count == 1:
        await _redis.expire(key, seconds)
    return count > times


def _memory_limited(key: str, times: int, seconds: int) -> bool:
    now = time.monotonic()
    count, window_start = _memory[key]
    if now - window_start >= seconds:
        _memory[key] = (1, now)
        return False
    count += 1
    _memory[key] = (count, window_start)
    return count > times
