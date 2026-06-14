from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserSession


async def create_session(
    session: AsyncSession,
    *,
    user_id: str,
    refresh_token_jti: str,
    expires_at: datetime,
    device_type: str | None = None,
    device_name: str | None = None,
    browser: str | None = None,
    os: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> UserSession:
    db_session = UserSession(
        user_id=user_id,
        refresh_token_jti=refresh_token_jti,
        expires_at=expires_at,
        device_type=device_type,
        device_name=device_name,
        browser=browser,
        os=os,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(db_session)
    await session.commit()
    await session.refresh(db_session)
    return db_session


async def find_by_refresh_token_jti(session: AsyncSession, jti: str) -> UserSession | None:
    result = await session.execute(select(UserSession).where(UserSession.refresh_token_jti == jti))
    return result.scalar_one_or_none()


async def find_active_by_user_id(session: AsyncSession, user_id: str) -> list[UserSession]:
    now = datetime.now(UTC)
    result = await session.execute(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),  # type: ignore
            UserSession.expires_at > now,
        )
    )
    return list(result.scalars().all())


async def revoke_session(session: AsyncSession, db_session: UserSession) -> UserSession:
    db_session.revoked_at = datetime.now(UTC)
    session.add(db_session)
    await session.commit()
    await session.refresh(db_session)
    return db_session


async def revoke_all_user_sessions(session: AsyncSession, user_id: str) -> int:
    now = datetime.now(UTC)
    sessions = await find_active_by_user_id(session, user_id)
    for s in sessions:
        s.revoked_at = now
        session.add(s)
    await session.commit()
    return len(sessions)


async def delete_expired(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    result = await session.execute(select(UserSession).where(UserSession.expires_at < now))
    expired = list(result.scalars().all())
    for s in expired:
        await session.delete(s)
    await session.commit()
    return len(expired)
