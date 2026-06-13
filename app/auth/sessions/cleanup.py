"""Scheduled cleanup for expired sessions. Run this as a cron job or background task."""

import logging

from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import repositories as repo

logger = logging.getLogger("fastauth.sessions.cleanup")


async def delete_expired_sessions(session: AsyncSession) -> int:
    count = await repo.session.delete_expired(session)
    logger.info("session cleanup complete", extra={"deleted": count})
    return count
