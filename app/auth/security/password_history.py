"""Password history — prevent reuse of last N passwords."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import verify_password

_HISTORY_DEPTH = 5


async def check_password_not_reused(
    session: AsyncSession, user_id: str, new_password: str
) -> bool:
    """Return True if new_password is safe (not in recent history)."""
    from app.auth.db_models import PasswordHistory

    result = await session.exec(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user_id)
        .order_by(PasswordHistory.created_at.desc())  # type: ignore[attr-defined]
        .limit(_HISTORY_DEPTH)
    )
    for row in result.all():
        if verify_password(new_password, row.hashed_password):
            return False
    return True


async def add_password_to_history(
    session: AsyncSession, user_id: str, hashed_password: str
) -> None:
    """Record hashed_password in history; prune beyond _HISTORY_DEPTH entries."""
    from app.auth.db_models import PasswordHistory

    entry = PasswordHistory(user_id=user_id, hashed_password=hashed_password)
    session.add(entry)
    await session.commit()

    # Prune oldest entries beyond depth
    result = await session.exec(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user_id)
        .order_by(PasswordHistory.created_at.desc())  # type: ignore[attr-defined]
    )
    all_rows = list(result.all())
    for old in all_rows[_HISTORY_DEPTH:]:
        await session.delete(old)
    if len(all_rows) > _HISTORY_DEPTH:
        await session.commit()
