from datetime import datetime

from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    id: str
    resource: str
    action: str
    description: str | None

    class Config:
        from_attributes = True


class CreateRoleRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateRoleRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class AssignPermissionRequest(BaseModel):
    permission_id: str


class AssignRoleRequest(BaseModel):
    role_id: str
