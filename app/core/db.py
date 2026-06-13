from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

_kwargs: dict = {"echo": False}
if not settings.is_sqlite:
    _kwargs.update(
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        # recycle prevents stale connections dropped by PgBouncer or cloud load balancers
        pool_recycle=1800,
    )

engine = create_async_engine(settings.async_database_url, **_kwargs)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
