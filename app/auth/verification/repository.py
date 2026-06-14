from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import EmailVerificationToken


async def invalidate_pending(session: AsyncSession, user_id: str) -> None:
    await session.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used_at.is_(None),  # type: ignore
        )
        .values(used_at=datetime.now(UTC))
    )


async def save(session: AsyncSession, token: EmailVerificationToken) -> None:
    session.add(token)


async def find_valid_token(
    session: AsyncSession, token_hash: str
) -> EmailVerificationToken | None:
    result = await session.execute(
        select(EmailVerificationToken)
        .where(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used_at.is_(None),  # type: ignore
            EmailVerificationToken.expires_at > datetime.now(UTC),
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def mark_used(session: AsyncSession, token: EmailVerificationToken) -> None:
    token.used_at = datetime.now(UTC)
    session.add(token)
