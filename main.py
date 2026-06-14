import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app as _make_metrics_app
from redis.asyncio import from_url
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from app.shared.database import Base as _Base

import app.auth.db_models as _auth_db_models  # noqa: F401 — register extended models for SQLModel.metadata
import app.auth.models as _auth_models  # noqa: F401 — register models for SQLModel.metadata
from app.admin.router import router as admin_router
from app.auth.api_keys.router import router as api_keys_router
from app.auth.audit.router import router as audit_router
from app.auth.mfa.router import router as mfa_router
from app.auth.oauth.router import router as oauth_router
from app.auth.rbac.router import router as rbac_router
from app.auth.password.router import router as password_router
from app.auth.router import router as auth_router
from app.auth.verification.router import router as verification_router
from app.auth.sessions.router import router as sessions_router
from app.auth.social.router import router as social_router
from app.core.config import settings
from app.core.db import engine as _db_engine
from app.core.limiter import close_redis, set_redis
from app.core.logging import setup_logging
from app.core.middleware import (
    LoggerMiddleware,
    MetricsMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
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

_MIGRATE_MAX_ATTEMPTS = 10
_MIGRATE_BACKOFF_SECONDS = 2


def _migrate() -> None:
    if settings.is_sqlite:
        engine = create_engine(settings.database_url)
        _Base.metadata.create_all(engine)
        engine.dispose()
    else:
        command.upgrade(Config(str(_ALEMBIC_INI)), "head")


async def _migrate_with_retry() -> None:
    for attempt in range(1, _MIGRATE_MAX_ATTEMPTS + 1):
        try:
            _migrate()
            return
        except OperationalError as exc:
            if attempt == _MIGRATE_MAX_ATTEMPTS:
                raise
            logger.warning(
                "DB not ready, retrying migration",
                extra={"attempt": attempt, "error": str(exc)},
            )
            await asyncio.sleep(_MIGRATE_BACKOFF_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _migrate_with_retry()
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


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exc_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggerMiddleware)
app.add_middleware(RequestIDMiddleware)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

instrument_app(app)
instrument_sqlalchemy(_db_engine)

app.mount("/metrics", _make_metrics_app())

app.include_router(web_router)
app.include_router(auth_router)
app.include_router(password_router)
app.include_router(verification_router)
app.include_router(mfa_router)
app.include_router(sessions_router)
app.include_router(social_router)
app.include_router(rbac_router)
app.include_router(audit_router)
app.include_router(admin_router)
app.include_router(oauth_router)
app.include_router(api_keys_router)
app.include_router(health_router)
