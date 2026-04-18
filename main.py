from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from redis.asyncio import from_url

from app.core.config import settings
from app.auth.router import router as auth_router
from app.health.router import router as health_router

_ALEMBIC_INI = Path(__file__).resolve().parent / "alembic.ini"


def _migrate() -> None:
    command.upgrade(Config(str(_ALEMBIC_INI)), "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _migrate()
    redis = from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)
    yield
    await FastAPILimiter.close()


app = FastAPI(title="FastAuth", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(health_router)
