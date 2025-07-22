from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class HealthResponse(BaseModel):
    """Health check response model."""
    message: str = "FastAuth is healthy"
    status: HealthStatus = HealthStatus.HEALTHY
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
