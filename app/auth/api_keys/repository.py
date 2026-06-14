from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_keys.utils import generate_api_key
from app.auth.db_models import APIKey


async def create(
    session: AsyncSession,
    *,
    owner_user_id: str,
    name: str,
    scopes: list[str],
    expires_at: datetime | None = None,
) -> tuple[APIKey, str]:
    """Create a new API key. Returns (db_row, raw_key) — raw_key shown once only."""
    raw_key, key_hash = generate_api_key()
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        scopes=" ".join(scopes),
        owner_user_id=owner_user_id,
        expires_at=expires_at,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key, raw_key


async def find_by_hash(session: AsyncSession, key_hash: str) -> APIKey | None:
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    return result.scalar_one_or_none()


async def list_for_user(session: AsyncSession, user_id: str) -> list[APIKey]:
    result = await session.execute(
        select(APIKey).where(APIKey.owner_user_id == user_id).order_by(APIKey.created_at)  # type: ignore
    )
    return list(result.scalars().all())


async def revoke(session: AsyncSession, key_id: str, owner_user_id: str) -> bool:
    api_key = await session.get(APIKey, key_id)
    if api_key is None or api_key.owner_user_id != owner_user_id:
        return False
    if api_key.revoked_at is not None:
        return False
    api_key.revoked_at = datetime.now(UTC)
    session.add(api_key)
    await session.commit()
    return True
