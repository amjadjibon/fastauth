from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserMfaBackupCode, UserMfaSecret


async def find_secret(session: AsyncSession, user_id: str) -> UserMfaSecret | None:
    result = await session.execute(select(UserMfaSecret).where(UserMfaSecret.user_id == user_id))
    return result.scalar_one_or_none()


async def save_secret(session: AsyncSession, mfa: UserMfaSecret) -> UserMfaSecret:
    session.add(mfa)
    await session.commit()
    await session.refresh(mfa)
    return mfa


async def delete_secret(session: AsyncSession, mfa: UserMfaSecret) -> None:
    await session.delete(mfa)
    await session.commit()


async def replace_backup_codes(
    session: AsyncSession, user_id: str, code_hashes: list[str]
) -> None:
    result = await session.execute(
        select(UserMfaBackupCode).where(UserMfaBackupCode.user_id == user_id)
    )
    for code in result.scalars().all():
        await session.delete(code)
    for h in code_hashes:
        session.add(UserMfaBackupCode(user_id=user_id, code_hash=h))
    await session.commit()


async def find_unused_backup_code(
    session: AsyncSession, user_id: str, code_hash: str
) -> UserMfaBackupCode | None:
    result = await session.execute(
        select(UserMfaBackupCode).where(
            UserMfaBackupCode.user_id == user_id,
            UserMfaBackupCode.code_hash == code_hash,
            UserMfaBackupCode.used_at.is_(None),  # type: ignore
        )
    )
    return result.scalar_one_or_none()


async def mark_backup_code_used(session: AsyncSession, code: UserMfaBackupCode) -> None:
    code.used_at = datetime.now(UTC)
    session.add(code)
    await session.commit()
