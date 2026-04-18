from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from redis.asyncio import from_url

from app.core.config import settings
from app.core.limiter import close_redis, set_redis
from app.core.logging import setup_logging
from app.core.middleware import LoggerMiddleware, RequestIDMiddleware

setup_logging()
from app.auth.router import router as auth_router
from app.health.router import router as health_router

_ALEMBIC_INI = Path(__file__).resolve().parent / "alembic.ini"


def _migrate() -> None:
    command.upgrade(Config(str(_ALEMBIC_INI)), "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _migrate()
    set_redis(from_url(settings.redis_url, encoding="utf-8", decode_responses=True))
    yield
    await close_redis()


app = FastAPI(title="FastAuth", lifespan=lifespan)

app.add_middleware(LoggerMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(auth_router)
app.include_router(health_router)
