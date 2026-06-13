from datetime import datetime

from pydantic import BaseModel


class UserListResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime
    is_locked: bool = False

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    roles: list[str] = []
    mfa_enabled: bool = False
    active_sessions: int = 0
    is_locked: bool = False

    class Config:
        from_attributes = True


class UpdateUserRequest(BaseModel):
    email: str | None = None
    username: str | None = None


class PaginatedUsersResponse(BaseModel):
    users: list[UserListResponse]
    total: int
    page: int
    limit: int


class DashboardMetrics(BaseModel):
    total_users: int
    active_sessions: int
    mfa_enabled_users: int
    failed_login_attempts_24h: int
