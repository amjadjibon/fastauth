from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.audit.events import AuditEvent
from app.auth.models import AuditLog


async def failed_login_attempts_24h(session: AsyncSession) -> int:
    since = datetime.now(UTC) - timedelta(hours=24)
    result = await session.execute(
        select(func.count()).where(
            AuditLog.event_type == AuditEvent.LOGIN_FAILED,
            AuditLog.created_at >= since,
        )
    )
    return result.scalar() or 0


async def active_sessions_count(session: AsyncSession) -> int:
    from app.auth.models import UserSession

    now = datetime.now(UTC)
    result = await session.execute(
        select(func.count()).where(
            UserSession.revoked_at.is_(None),  # type: ignore
            UserSession.expires_at > now,
        )
    )
    return result.scalar() or 0


async def mfa_enabled_users_count(session: AsyncSession) -> int:
    from app.auth.models import UserMfaSecret

    result = await session.execute(
        select(func.count()).where(UserMfaSecret.is_verified == True)  # noqa: E712
    )
    return result.scalar() or 0
