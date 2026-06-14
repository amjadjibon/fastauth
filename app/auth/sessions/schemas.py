from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra={"example": {
        "id": "00000000-0000-0000-0000-000000000001",
        "device_type": "desktop",
        "device_name": "My Laptop",
        "browser": "Chrome",
        "os": "macOS",
        "ip_address": "192.0.2.1",
        "last_active_at": "2024-01-01T12:00:00Z",
        "created_at": "2024-01-01T00:00:00Z",
        "expires_at": "2024-01-08T00:00:00Z",
        "is_current": True,
    }})

    id: str
    device_type: str | None
    device_name: str | None
    browser: str | None
    os: str | None
    ip_address: str | None
    last_active_at: datetime | None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


class SessionsListResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "sessions": [{
            "id": "00000000-0000-0000-0000-000000000001",
            "device_type": "desktop",
            "device_name": "My Laptop",
            "browser": "Chrome",
            "os": "macOS",
            "ip_address": "192.0.2.1",
            "last_active_at": "2024-01-01T12:00:00Z",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": "2024-01-08T00:00:00Z",
            "is_current": True,
        }],
        "total": 1,
    }})

    sessions: list[SessionResponse]
    total: int
