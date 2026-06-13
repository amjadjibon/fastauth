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


@router.get("/healthz/ready")
async def readiness():
    """Readiness probe: checks database, Redis, and returns dependency status."""
    checks: dict[str, str] = {}
    all_ok = True

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "error"
        all_ok = False

    # Redis check
    from app.core.limiter import _redis

    if _redis:
        try:
            await _redis.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "error"
            all_ok = False
    else:
        checks["redis"] = "not_configured"

    if not all_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "checks": checks},
        )
    return {"status": "ready", "checks": checks}


@router.get("/livez")
def livez():
    return {"status": "alive"}
