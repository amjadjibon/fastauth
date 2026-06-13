from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.admin.models import DashboardMetrics
from app.auth.audit.reports import (
    active_sessions_count,
    failed_login_attempts_24h,
    mfa_enabled_users_count,
)
from app.auth.models import User


async def get_dashboard_metrics(session: AsyncSession) -> DashboardMetrics:
    user_count_result = await session.exec(select(func.count(User.id)))
    total_users = user_count_result.one() or 0

    return DashboardMetrics(
        total_users=total_users,
        active_sessions=await active_sessions_count(session),
        mfa_enabled_users=await mfa_enabled_users_count(session),
        failed_login_attempts_24h=await failed_login_attempts_24h(session),
    )
