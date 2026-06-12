from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.db import engine

router = APIRouter(tags=["ops"])


@router.get("/healthz")
async def healthz():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "db": "ok"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable"
        ) from exc


@router.get("/livez")
def livez():
    return {"status": "alive"}
