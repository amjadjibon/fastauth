from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import PasswordResetToken


async def find_valid_token(session: AsyncSession, token_hash: str) -> PasswordResetToken | None:
    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),  # type: ignore
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def save(session: AsyncSession, token: PasswordResetToken) -> None:
    session.add(token)
    await session.commit()


async def mark_used(session: AsyncSession, token: PasswordResetToken) -> None:
    token.used_at = datetime.now(UTC)
    session.add(token)
    await session.commit()
