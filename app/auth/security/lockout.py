"""Account lockout management — lock/unlock individual accounts."""

import logging

logger = logging.getLogger("fastauth.security.lockout")

_LOCKOUT_SECONDS = 900
_memory_store: dict[str, bool] = {}


async def lock_account(user_id: str, redis=None) -> None:
    logger.warning("Account locked", extra={"user_id": user_id})
    if redis:
        await redis.setex(f"account:locked:{user_id}", _LOCKOUT_SECONDS, "1")
    else:
        _memory_store[user_id] = True


async def is_account_locked(user_id: str, redis=None) -> bool:
    if redis:
        return bool(await redis.exists(f"account:locked:{user_id}"))
    return _memory_store.get(user_id, False)


async def unlock_account(user_id: str, redis=None) -> None:
    logger.info("Account unlocked", extra={"user_id": user_id})
    if redis:
        await redis.delete(f"account:locked:{user_id}")
    else:
        _memory_store.pop(user_id, None)
