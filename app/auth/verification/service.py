import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import EmailVerificationToken, User
from app.auth.verification import repository as repo
from app.core.email import send_verification_email


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

_EXPIRE_HOURS = 24


async def issue_verification_token(session: AsyncSession, user: User, *, commit: bool = True) -> str:
    """Invalidate pending tokens, stage a new one, optionally commit and send email."""
    await repo.invalidate_pending(session, user.id)

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(hours=_EXPIRE_HOURS)
    await repo.save(session, EmailVerificationToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))

    if commit:
        await session.commit()
        await send_verification_email(user.id, user.email, raw_token)

    return raw_token


async def verify_email(
    session: AsyncSession, token_raw: str
) -> tuple[User | None, str | None]:
    """Validate token, mark user verified. Return (user, error_detail)."""
    token_hash = _hash_token(token_raw)
    vtoken = await repo.find_valid_token(session, token_hash)
    if vtoken is None:
        return None, "Invalid or expired token"

    from app.auth.repositories.user_repository import find_by_id
    user = await find_by_id(session, vtoken.user_id)
    if user is None:
        return None, "User not found"

    await repo.mark_used(session, vtoken)
    user.email_verified = True
    session.add(user)
    await session.commit()
    return user, None
