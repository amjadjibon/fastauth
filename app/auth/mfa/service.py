from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.mfa import repository as repo
from app.auth.mfa.domain import generate_backup_codes, hash_backup_code, verify_totp
from app.auth.models import UserMfaSecret


async def enable_mfa(session: AsyncSession, user_id: str, encrypted_secret: str) -> UserMfaSecret:
    existing = await repo.find_secret(session, user_id)
    if existing:
        existing.secret_encrypted = encrypted_secret
        existing.is_verified = False
        existing.verified_at = None
        return await repo.save_secret(session, existing)
    return await repo.save_secret(session, UserMfaSecret(user_id=user_id, secret_encrypted=encrypted_secret))


async def verify_totp_and_mark(session: AsyncSession, user_id: str) -> bool:
    mfa = await repo.find_secret(session, user_id)
    if mfa is None:
        return False
    mfa.is_verified = True
    mfa.verified_at = datetime.now(UTC)
    await repo.save_secret(session, mfa)
    return True


async def generate_and_store_backup_codes(session: AsyncSession, user_id: str) -> list[str]:
    plain_codes = generate_backup_codes(10)
    hashes = [hash_backup_code(c) for c in plain_codes]
    await repo.replace_backup_codes(session, user_id, hashes)
    return plain_codes


async def verify_backup_code(session: AsyncSession, user_id: str, plain_code: str) -> bool:
    h = hash_backup_code(plain_code)
    code_obj = await repo.find_unused_backup_code(session, user_id, h)
    if code_obj is None:
        return False
    await repo.mark_backup_code_used(session, code_obj)
    return True


async def is_mfa_enabled(session: AsyncSession, user_id: str) -> bool:
    mfa = await repo.find_secret(session, user_id)
    return mfa is not None and mfa.is_verified


async def get_mfa_secret(session: AsyncSession, user_id: str) -> UserMfaSecret | None:
    return await repo.find_secret(session, user_id)


async def disable_mfa(session: AsyncSession, user_id: str) -> bool:
    mfa = await repo.find_secret(session, user_id)
    if mfa is None:
        return False
    await repo.delete_secret(session, mfa)
    return True
