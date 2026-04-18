import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel

from app.core.db import engine
from main import app


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
