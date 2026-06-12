import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from prometheus_client import make_asgi_app as _make_metrics_app
from redis.asyncio import from_url
from sqlalchemy import create_engine
from sqlmodel import SQLModel

import app.auth.models  # noqa: F401 — register models for SQLModel.metadata
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.db import engine as _db_engine
from app.core.limiter import close_redis, set_redis
from app.core.logging import setup_logging
from app.core.middleware import LoggerMiddleware, MetricsMiddleware, RequestIDMiddleware
from app.core.telemetry import (
    instrument_app,
    instrument_redis,
    instrument_sqlalchemy,
    setup_telemetry,
)
from app.health.router import router as health_router
from app.web.router import router as web_router

setup_logging()
setup_telemetry()

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
        redis_client = from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        set_redis(redis_client)
        instrument_redis(redis_client)
        logger.info("redis connected", extra={"url": settings.redis_url})
    else:
        logger.warning("redis not configured, using in-memory rate limiting")

    logger.info("startup complete")
    yield
    await close_redis()
    logger.info("shutdown complete")


app = FastAPI(title="FastAuth", lifespan=lifespan)

app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggerMiddleware)
app.add_middleware(RequestIDMiddleware)

instrument_app(app)
instrument_sqlalchemy(_db_engine)

app.mount("/metrics", _make_metrics_app())

app.include_router(web_router)
app.include_router(auth_router)
app.include_router(health_router)
