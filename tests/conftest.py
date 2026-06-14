import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
import app.auth.db_models as _db_models  # noqa: F401 — registers ORM models with Base.metadata
import app.auth.models as _models  # noqa: F401
from app.core.db import engine
from app.shared.database import Base
from main import app as fastapi_app


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
        yield c

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
