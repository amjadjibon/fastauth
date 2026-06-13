from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    sessions: list[SessionResponse]
    total: int
