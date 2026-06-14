from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlmodel import SQLModel

from app.core.config import settings

_kwargs: dict = {"echo": False}
if not settings.is_sqlite:
    _kwargs.update(
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )

engine = create_async_engine(settings.async_database_url, **_kwargs)


class Base(DeclarativeBase):
    # Share SQLModel's metadata so existing SQLModel table=True models
    # are visible to Base.metadata.create_all during the migration.
    metadata = SQLModel.metadata


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
