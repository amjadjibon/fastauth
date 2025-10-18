import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from fastauth.api import setup_routers
from fastauth.core.config import settings
from fastauth.db.session import init_db
from fastauth.middleware.exception import ExceptionHandlerMiddleware
from fastauth.middleware.logging import LoggingMiddleware
from fastauth.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan events."""
    logger.info("starting up fastauth...")
    await init_db()

    yield
    logger.info("shutting down fastauth...")


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(ExceptionHandlerMiddleware, debug=settings.debug)
app.add_middleware(LoggingMiddleware, log_level=logging.INFO)
app.add_middleware(RequestIDMiddleware)

setup_routers(app)
