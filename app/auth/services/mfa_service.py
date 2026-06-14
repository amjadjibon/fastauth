import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserMfaBackupCode, UserMfaSecret


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


async def enable_mfa(session: AsyncSession, user_id: str, encrypted_secret: str) -> UserMfaSecret:
    existing = await _get_mfa_secret(session, user_id)
    if existing:
        existing.secret_encrypted = encrypted_secret
        existing.is_verified = False
        existing.verified_at = None
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return existing

    mfa = UserMfaSecret(user_id=user_id, secret_encrypted=encrypted_secret)
    session.add(mfa)
    await session.commit()
    await session.refresh(mfa)
    return mfa


async def verify_totp(session: AsyncSession, user_id: str, code: str) -> bool:
    """Mark MFA as verified after TOTP code confirms the secret is correct."""
    mfa = await _get_mfa_secret(session, user_id)
    if mfa is None:
        return False
    # Actual TOTP verification is done at the route layer using pyotp;
    # this method records the verification event.
    mfa.is_verified = True
    mfa.verified_at = datetime.now(UTC)
    session.add(mfa)
    await session.commit()
    return True


async def generate_backup_codes(session: AsyncSession, user_id: str) -> list[str]:
    # Delete old backup codes
    result = await session.execute(select(UserMfaBackupCode).where(UserMfaBackupCode.user_id == user_id))
    for code in result.scalars().all():
        await session.delete(code)

    plain_codes: list[str] = []
    for _ in range(10):
        plain = secrets.token_hex(4).upper()  # 8-char hex code
        code_obj = UserMfaBackupCode(user_id=user_id, code_hash=_hash_code(plain))
        session.add(code_obj)
        plain_codes.append(plain)

    await session.commit()
    return plain_codes


async def verify_backup_code(session: AsyncSession, user_id: str, plain_code: str) -> bool:
    code_hash = _hash_code(plain_code)
    result = await session.execute(
        select(UserMfaBackupCode).where(
            UserMfaBackupCode.user_id == user_id,
            UserMfaBackupCode.code_hash == code_hash,
            UserMfaBackupCode.used_at.is_(None),  # type: ignore
        )
    )
    code_obj = result.scalar_one_or_none()
    if code_obj is None:
        return False
    code_obj.used_at = datetime.now(UTC)
    session.add(code_obj)
    await session.commit()
    return True


async def is_mfa_enabled(session: AsyncSession, user_id: str) -> bool:
    mfa = await _get_mfa_secret(session, user_id)
    return mfa is not None and mfa.is_verified


async def get_mfa_secret(session: AsyncSession, user_id: str) -> UserMfaSecret | None:
    return await _get_mfa_secret(session, user_id)


async def _get_mfa_secret(session: AsyncSession, user_id: str) -> UserMfaSecret | None:
    result = await session.execute(select(UserMfaSecret).where(UserMfaSecret.user_id == user_id))
    return result.scalar_one_or_none()
