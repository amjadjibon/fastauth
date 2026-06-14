import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import PasswordResetToken, User
from app.auth.password import repository as repo
from app.auth.security.password_history import add_password_to_history, check_password_not_reused
from app.core.security import hash_password, verify_password

logger = logging.getLogger("fastauth.auth")

_RESET_TOKEN_TTL_MINUTES = 10


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def issue_reset_token(session: AsyncSession, user: User) -> str:
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(minutes=_RESET_TOKEN_TTL_MINUTES)
    await repo.save(session, PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    logger.debug("Password reset token issued for user %s", user.id)
    return raw_token


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> tuple[bool, str | None]:
    """Return (ok, error_detail)."""
    if not verify_password(current_password, user.hashed_password):
        return False, "Current password is incorrect"
    if not await check_password_not_reused(session, user.id, new_password):
        return False, "Password was recently used"
    await add_password_to_history(session, user.id, user.hashed_password)
    user.hashed_password = hash_password(new_password)
    session.add(user)
    await session.commit()
    return True, None


async def reset_password(
    session: AsyncSession, token_raw: str, new_password: str
) -> tuple[User | None, str | None]:
    """Validate reset token, update password, return (user, error_detail)."""
    token_hash = _hash_token(token_raw)
    reset_token = await repo.find_valid_token(session, token_hash)
    if reset_token is None:
        return None, "Invalid or expired reset token"

    from app.auth.repositories.user_repository import find_by_id
    user = await find_by_id(session, reset_token.user_id)
    if user is None:
        return None, "User not found"

    if not await check_password_not_reused(session, user.id, new_password):
        return None, "Password was recently used"

    await add_password_to_history(session, user.id, user.hashed_password)
    user.hashed_password = hash_password(new_password)
    await repo.mark_used(session, reset_token)
    session.add(user)
    await session.commit()
    return user, None
