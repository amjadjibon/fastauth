from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
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

    class Config:
        from_attributes = True


class SessionsListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int
