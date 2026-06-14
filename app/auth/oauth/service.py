import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.oauth import repository as repo
from app.core.security import create_token, decode_token


async def authorize_client(
    session: AsyncSession,
    client_id: str,
    redirect_uri: str,
    user_id: str,
    scopes: str,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    nonce: str | None = None,
) -> str | None:
    client = await repo.find_client_by_id(session, client_id)
    if client is None or not client.is_active:
        return None
    if redirect_uri not in client.redirect_uris.split():
        return None

    code = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    await repo.create_authorization_code(
        session,
        code=code,
        client_id=client_id,
        user_id=user_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
        expires_at=expires_at,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        nonce=nonce,
    )
    return code


async def exchange_code_for_token(
    session: AsyncSession,
    code: str,
    client_id: str,
    redirect_uri: str,
    code_verifier: str | None = None,
) -> dict | None:
    auth_code = await repo.consume_authorization_code(session, code)
    if auth_code is None:
        return None
    if auth_code.client_id != client_id:
        return None
    if auth_code.redirect_uri != redirect_uri:
        return None

    access_token = create_token(
        {"sub": auth_code.user_id, "type": "access", "scope": auth_code.scopes},
        timedelta(hours=1),
    )
    refresh_raw = secrets.token_urlsafe(32)
    return {
        "access_token": access_token,
        "refresh_token": refresh_raw,
        "token_type": "bearer",
        "expires_in": 3600,
        "scope": auth_code.scopes,
    }


async def validate_token(token: str) -> dict | None:
    try:
        return decode_token(token)
    except Exception:
        return None
