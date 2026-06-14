from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import APIKey


async def save(session: AsyncSession, api_key: APIKey) -> APIKey:
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key


async def find_by_hash(session: AsyncSession, key_hash: str) -> APIKey | None:
    result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    return result.scalar_one_or_none()


async def find_by_id(session: AsyncSession, key_id: str) -> APIKey | None:
    return await session.get(APIKey, key_id)


async def list_for_user(session: AsyncSession, user_id: str) -> list[APIKey]:
    result = await session.execute(
        select(APIKey).where(APIKey.owner_user_id == user_id).order_by(APIKey.created_at)  # type: ignore
    )
    return list(result.scalars().all())


async def update_last_used(session: AsyncSession, api_key: APIKey, timestamp: datetime) -> None:
    api_key.last_used_at = timestamp
    session.add(api_key)
    await session.commit()


async def set_revoked(session: AsyncSession, api_key: APIKey) -> None:
    api_key.revoked_at = datetime.now(UTC)
    session.add(api_key)
    await session.commit()
