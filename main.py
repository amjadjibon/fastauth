from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.core.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="FastAuth", lifespan=lifespan)

app.include_router(auth_router)


@app.get("/")
def health():
    return {"status": "ok"}
