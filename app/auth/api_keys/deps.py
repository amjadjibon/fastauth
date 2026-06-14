from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.auth.api_keys.domain import APIKeyPrincipal
from app.auth.api_keys import service
from app.auth.deps import SessionDep

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
    return await service.authenticate(session, raw_key)


APIKeyDep = Annotated[APIKeyPrincipal, Depends(get_api_key_principal)]
