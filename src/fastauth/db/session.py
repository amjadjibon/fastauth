from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from fastauth.core.config import settings

# Configure engine based on database type
engine_kwargs = {"echo": settings.debug}

# SQLite specific configuration
if settings.database_url.startswith("sqlite"):
    engine_kwargs.update(
        {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    )

engine = create_async_engine(settings.database_url, **engine_kwargs)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        if settings.debug:
            await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Get database session."""
    async with async_session() as session:
        yield session
