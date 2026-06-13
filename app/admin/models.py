from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    created_at: datetime
    is_locked: bool = False


class UserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    roles: list[str] = []
    mfa_enabled: bool = False
    active_sessions: int = 0
    is_locked: bool = False


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


class OAuthClientCreateRequest(BaseModel):
    name: str
    redirect_uris: list[str]
    scopes: list[str] = ["openid", "profile", "email"]
    is_confidential: bool = True


class OAuthClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    redirect_uris: str
    scopes: str
    is_confidential: bool
    is_active: bool
    created_at: datetime
