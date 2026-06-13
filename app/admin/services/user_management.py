from datetime import UTC, datetime

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.db_models import UserMfaSecret, UserSession
from app.auth.models import User
from app.auth.rbac.repositories import role_repository
from app.auth.security.lockout import is_account_locked, lock_account, unlock_account


async def list_users(
    session: AsyncSession,
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
    status: str | None = None,
) -> tuple[list[User], int]:
    query = select(User)
    if search:
        query = query.where(
            User.username.contains(search) | User.email.contains(search)  # type: ignore
        )
    count_result = await session.exec(select(func.count()))
    total = count_result.one() or 0
    query = query.offset((page - 1) * limit).limit(limit)
    result = await session.exec(query)
    return list(result.all()), total


async def get_user_detail(session: AsyncSession, user_id: str) -> dict | None:
    user = await session.get(User, user_id)
    if user is None:
        return None

    roles = await role_repository.get_user_roles(session, user_id)
    mfa_result = await session.exec(
        select(UserMfaSecret).where(UserMfaSecret.user_id == user_id, UserMfaSecret.is_verified)
    )
    mfa_enabled = mfa_result.first() is not None

    now = datetime.now(UTC)
    session_result = await session.exec(
        select(func.count()).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),  # type: ignore
            UserSession.expires_at > now,
        )
    )
    active_sessions = session_result.one() or 0
    locked = await is_account_locked(user_id)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "roles": [r.name for r in roles],
        "mfa_enabled": mfa_enabled,
        "active_sessions": active_sessions,
        "is_locked": locked,
    }


async def lock_user(user_id: str, redis=None) -> None:
    await lock_account(user_id, redis=redis)


async def unlock_user(user_id: str, redis=None) -> None:
    await unlock_account(user_id, redis=redis)


async def force_password_reset(session: AsyncSession, user_id: str) -> bool:
    user = await session.get(User, user_id)
    return user is not None
