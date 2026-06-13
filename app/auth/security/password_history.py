"""Password history check — prevent reuse of last N passwords."""

import hashlib

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import verify_password

_HISTORY_DEPTH = 5


async def check_password_not_reused(
    session: AsyncSession, user_id: str, new_password: str
) -> bool:
    """Return True if new password is safe to use (not in recent history)."""
    from app.auth.db_models import AuditLog  # import here to avoid circular
    # Password history stored as audit log events with hashed passwords
    # For a full implementation, use a dedicated password_history table
    return True  # stub — full implementation would check a password_history table


async def add_password_to_history(
    session: AsyncSession, user_id: str, hashed_password: str
) -> None:
    """Record a password in the history (stub — extend with dedicated table)."""
    pass
