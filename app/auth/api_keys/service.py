import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_keys import repository as repo
from app.auth.api_keys.domain import APIKeyPrincipal, generate_api_key, hash_api_key
from app.auth.models import APIKey

logger = logging.getLogger("fastauth")


async def create(
    session: AsyncSession,
    *,
    owner_user_id: str,
    name: str,
    scopes: list[str],
    expires_at: datetime | None = None,
) -> tuple[APIKey, str]:
    raw_key, key_hash = generate_api_key()
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        scopes=" ".join(scopes),
        owner_user_id=owner_user_id,
        expires_at=expires_at,
    )
    return await repo.save(session, api_key), raw_key


async def list_for_user(session: AsyncSession, user_id: str) -> list[APIKey]:
    return await repo.list_for_user(session, user_id)


async def revoke(session: AsyncSession, key_id: str, owner_user_id: str) -> bool:
    api_key = await repo.find_by_id(session, key_id)
    if api_key is None or api_key.owner_user_id != owner_user_id:
        return False
    if api_key.revoked_at is not None:
        return False
    await repo.set_revoked(session, api_key)
    return True


async def authenticate(session: AsyncSession, raw_key: str) -> APIKeyPrincipal:
    key_hash = hash_api_key(raw_key)
    api_key = await repo.find_by_hash(session, key_hash)

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if api_key.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key revoked")

    now = datetime.now(UTC)
    if api_key.expires_at is not None and api_key.expires_at.replace(tzinfo=UTC) < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    try:
        await repo.update_last_used(session, api_key, now)
    except Exception:
        logger.warning("api_key: failed to update last_used_at for key %s", api_key.id)

    return APIKeyPrincipal(
        key_id=api_key.id,
        owner_user_id=api_key.owner_user_id,
        scopes=api_key.scopes.split() if api_key.scopes else [],
    )
