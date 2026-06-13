from datetime import timedelta

from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import repositories as repo
from app.auth.db_models import UserSession
from app.core.config import settings
from app.core.security import create_token, decode_token

import uuid
from datetime import UTC, datetime


def _make_jti() -> str:
    return str(uuid.uuid4())


async def create_session(
    session: AsyncSession,
    *,
    user_id: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    device_type: str | None = None,
    device_name: str | None = None,
    browser: str | None = None,
    os: str | None = None,
) -> tuple[str, str, UserSession]:
    """Create session, returning (access_token, refresh_token, session)."""
    jti = _make_jti()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.refresh_token_expire_seconds)

    access_token = create_token(
        {"sub": user_id, "type": "access", "jti": jti},
        timedelta(seconds=settings.access_token_expire_seconds),
    )
    refresh_token = create_token(
        {"sub": user_id, "type": "refresh", "jti": jti},
        timedelta(seconds=settings.refresh_token_expire_seconds),
    )

    db_session = await repo.session.create_session(
        session,
        user_id=user_id,
        refresh_token_jti=jti,
        expires_at=expires_at,
        device_type=device_type,
        device_name=device_name,
        browser=browser,
        os=os,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return access_token, refresh_token, db_session


async def refresh_session(
    session: AsyncSession, refresh_token: str
) -> tuple[str, str, UserSession] | None:
    """Validate refresh token, revoke old session, return new token pair."""
    try:
        payload = decode_token(refresh_token)
    except Exception:
        return None

    if payload.get("type") != "refresh":
        return None

    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or not user_id:
        return None

    db_session = await repo.session.find_by_refresh_token_jti(session, jti)
    if db_session is None or db_session.revoked_at is not None:
        return None
    expires_at = db_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        return None

    # Rotate: revoke old session, create new one
    await repo.session.revoke_session(session, db_session)
    return await create_session(
        session,
        user_id=user_id,
        ip_address=db_session.ip_address,
        user_agent=db_session.user_agent,
        device_type=db_session.device_type,
        device_name=db_session.device_name,
        browser=db_session.browser,
        os=db_session.os,
    )


async def revoke_session_by_jti(session: AsyncSession, jti: str, user_id: str) -> bool:
    """Revoke a session identified by its refresh_token_jti (embedded in the access token)."""
    db_session = await repo.session.find_by_refresh_token_jti(session, jti)
    if db_session is None or db_session.user_id != user_id:
        return False
    if db_session.revoked_at is not None:
        return False
    await repo.session.revoke_session(session, db_session)
    return True


async def revoke_all_user_sessions(session: AsyncSession, user_id: str) -> int:
    return await repo.session.revoke_all_user_sessions(session, user_id)


async def revoke_session(session: AsyncSession, session_id: str, user_id: str) -> bool:
    db_session = await session.get(UserSession, session_id)
    if db_session is None or db_session.user_id != user_id:
        return False
    if db_session.revoked_at is not None:
        return False
    await repo.session.revoke_session(session, db_session)
    return True


async def list_active_sessions(session: AsyncSession, user_id: str) -> list[UserSession]:
    return await repo.session.find_active_by_user_id(session, user_id)
