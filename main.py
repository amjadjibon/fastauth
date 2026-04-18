import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.health.router import router as health_router

_ALEMBIC_INI = Path(__file__).resolve().parent / "alembic.ini"


def _migrate() -> None:
    command.upgrade(Config(str(_ALEMBIC_INI)), "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(_migrate)
    yield


app = FastAPI(title="FastAuth", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(health_router)
