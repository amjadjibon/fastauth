import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from redis.asyncio import from_url
from sqlalchemy import create_engine
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.limiter import close_redis, set_redis
from app.core.logging import setup_logging
from app.core.middleware import LoggerMiddleware, RequestIDMiddleware

setup_logging()

import app.auth.models  # noqa: F401 — register models for SQLModel.metadata
from app.auth.router import router as auth_router
from app.health.router import router as health_router
from app.web.router import router as web_router

_ALEMBIC_INI = Path(__file__).resolve().parent / "alembic.ini"
logger = logging.getLogger("fastauth")


def _migrate() -> None:
    if settings.is_sqlite:
        engine = create_engine(settings.database_url)
        SQLModel.metadata.create_all(engine)
        engine.dispose()
    else:
        command.upgrade(Config(str(_ALEMBIC_INI)), "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _migrate()
    logger.info("migrations applied")

    if settings.redis_url:
        set_redis(from_url(settings.redis_url, encoding="utf-8", decode_responses=True))
        logger.info("redis connected", extra={"url": settings.redis_url})
    else:
        logger.warning("redis not configured, using in-memory rate limiting")

    logger.info("startup complete")
    yield
    await close_redis()
    logger.info("shutdown complete")


app = FastAPI(title="FastAuth", lifespan=lifespan)

app.add_middleware(LoggerMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(web_router)
app.include_router(auth_router)
app.include_router(health_router)
