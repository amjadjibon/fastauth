from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
import uvicorn

from fastauth.api import setup_routers
from fastauth.core.config import settings
from fastauth.db.session import init_db


logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
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

setup_routers(app)

if __name__ == "__main__":
    uvicorn.run(
        "fastauth.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
