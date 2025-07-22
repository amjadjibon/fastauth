from fastapi import APIRouter

from fastauth.models.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()
