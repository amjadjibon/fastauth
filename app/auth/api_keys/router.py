from fastapi import APIRouter, HTTPException, status

from app.auth.api_keys import service
from app.auth.api_keys.deps import APIKeyDep
from app.auth.api_keys.schemas import APIKeyResponse, CreateAPIKeyRequest, CreateAPIKeyResponse
from app.auth.deps import CurrentUser, SessionDep

router = APIRouter(prefix="/auth/api-keys", tags=["api-keys"])


@router.post("", response_model=CreateAPIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(body: CreateAPIKeyRequest, current_user: CurrentUser, session: SessionDep):
    api_key, raw_key = await service.create(
        session,
        owner_user_id=current_user.id,
        name=body.name,
        scopes=body.scopes,
        expires_at=body.expires_at,
    )
    return CreateAPIKeyResponse(id=api_key.id, name=api_key.name, key=raw_key)


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(current_user: CurrentUser, session: SessionDep):
    keys = await service.list_for_user(session, current_user.id)
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            scopes=k.scopes.split() if k.scopes else [],
            created_at=k.created_at,
            expires_at=k.expires_at,
            revoked_at=k.revoked_at,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]


@router.get("/whoami")
async def whoami(principal: APIKeyDep):
    """Return the authenticated API key principal — use to verify a key is valid."""
    return {
        "key_id": principal.key_id,
        "owner_user_id": principal.owner_user_id,
        "scopes": principal.scopes,
    }


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: str, current_user: CurrentUser, session: SessionDep):
    revoked = await service.revoke(session, key_id, current_user.id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
