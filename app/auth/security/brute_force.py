"""Brute-force protection using Redis or in-memory fallback."""

import logging
from typing import Any

logger = logging.getLogger("fastauth.security.brute_force")

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300  # 5-minute window
_LOCKOUT_SECONDS = 900  # 15-minute lockout

_memory_store: dict[str, dict[str, Any]] = {}


class BruteForceProtection:
    """Track failed login attempts per IP and username using Redis when available."""

    def __init__(self, redis=None) -> None:
        self._redis = redis

    async def record_failed_attempt(self, key: str) -> int:
        """Increment failure counter; return current count."""
        if self._redis:
            pipe = self._redis.pipeline()
            attempt_key = f"bf:attempts:{key}"
            await pipe.incr(attempt_key)
            await pipe.expire(attempt_key, _WINDOW_SECONDS)
            results = await pipe.execute()
            return results[0]
        else:
            entry = _memory_store.setdefault(key, {"count": 0})
            entry["count"] += 1
            return entry["count"]

    async def is_blocked(self, key: str) -> bool:
        if self._redis:
            lockout_key = f"bf:lockout:{key}"
            return bool(await self._redis.exists(lockout_key))
        entry = _memory_store.get(key, {})
        return entry.get("locked", False)

    async def lock(self, key: str) -> None:
        logger.warning("Account/IP locked due to brute force", extra={"key": key})
        if self._redis:
            lockout_key = f"bf:lockout:{key}"
            await self._redis.setex(lockout_key, _LOCKOUT_SECONDS, "1")
        else:
            _memory_store.setdefault(key, {})["locked"] = True

    async def clear(self, key: str) -> None:
        if self._redis:
            await self._redis.delete(f"bf:attempts:{key}", f"bf:lockout:{key}")
        else:
            _memory_store.pop(key, None)

    async def check_and_record(self, username: str, ip: str) -> bool:
        """Return True if request should be blocked. Record the attempt."""
        for key in [f"user:{username}", f"ip:{ip}"]:
            if await self.is_blocked(key):
                return True
            count = await self.record_failed_attempt(key)
            if count >= _MAX_ATTEMPTS:
                await self.lock(key)
                return True
        return False


_instance: BruteForceProtection | None = None


def get_brute_force_protection(redis=None) -> BruteForceProtection:
    global _instance
    if _instance is None:
        _instance = BruteForceProtection(redis=redis)
    return _instance
