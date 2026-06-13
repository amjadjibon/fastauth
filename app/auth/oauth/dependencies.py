import hashlib

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.auth import repositories as repo
from app.auth.db_models import OAuthClient
from app.auth.deps import SessionDep

_basic = HTTPBasic(auto_error=False)


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


async def client_authenticated(
    session: SessionDep,
    credentials: HTTPBasicCredentials | None = Depends(_basic),
) -> OAuthClient:
    """Validate OAuth2 client credentials via HTTP Basic or form params."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    client = await repo.oauth.find_client_by_id(session, credentials.username)
    if client is None or not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client"
        )
    if client.is_confidential:
        if client.client_secret_hash != _hash_secret(credentials.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client secret"
            )
    return client


ClientAuthenticated = Depends(client_authenticated)
