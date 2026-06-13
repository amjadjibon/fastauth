import asyncio
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.auth.api_keys.models import APIKeyPrincipal
from app.auth.api_keys.repository import find_by_hash
from app.auth.api_keys.utils import hash_api_key
from app.auth.deps import SessionDep

logger = logging.getLogger("fastauth")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key_principal(
    raw_key: Annotated[str | None, Security(_api_key_header)],
    session: SessionDep,
) -> APIKeyPrincipal:
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header required",
        )

    key_hash = hash_api_key(raw_key)
    api_key = await find_by_hash(session, key_hash)

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if api_key.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key revoked")

    now = datetime.now(UTC)
    if api_key.expires_at is not None and api_key.expires_at.replace(tzinfo=UTC) < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    # Fire-and-forget last_used_at update — non-critical metadata.
    async def _update_last_used() -> None:
        try:
            api_key.last_used_at = now
            session.add(api_key)
            await session.commit()
        except Exception:
            logger.warning("api_key: failed to update last_used_at for key %s", api_key.id)

    asyncio.ensure_future(_update_last_used())

    return APIKeyPrincipal(
        key_id=api_key.id,
        owner_user_id=api_key.owner_user_id,
        scopes=api_key.scopes.split() if api_key.scopes else [],
    )


APIKeyDep = Annotated[APIKeyPrincipal, Depends(get_api_key_principal)]
