import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel

import app.auth.models as _models  # noqa: F401 — registers metadata before create_all
from app.core.db import engine
from main import app as fastapi_app


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
        yield c

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
