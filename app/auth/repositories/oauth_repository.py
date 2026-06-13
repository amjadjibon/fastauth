from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.db_models import OAuthAuthorizationCode, OAuthClient


async def find_client_by_id(session: AsyncSession, client_id: str) -> OAuthClient | None:
    return await session.get(OAuthClient, client_id)


async def create_authorization_code(
    session: AsyncSession,
    *,
    code: str,
    client_id: str,
    user_id: str,
    redirect_uri: str,
    scopes: str,
    expires_at: datetime,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    nonce: str | None = None,
) -> OAuthAuthorizationCode:
    auth_code = OAuthAuthorizationCode(
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
    session.add(auth_code)
    await session.commit()
    await session.refresh(auth_code)
    return auth_code


async def consume_authorization_code(
    session: AsyncSession, code: str
) -> OAuthAuthorizationCode | None:
    result = await session.exec(
        select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code)
    )
    auth_code = result.first()
    if auth_code is None:
        return None
    if auth_code.used_at is not None:
        return None  # already consumed
    if auth_code.expires_at < datetime.now(UTC):
        return None  # expired
    auth_code.used_at = datetime.now(UTC)
    session.add(auth_code)
    await session.commit()
    await session.refresh(auth_code)
    return auth_code
