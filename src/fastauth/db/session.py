from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from fastauth.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        yield session