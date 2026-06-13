from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    is_system: bool
    created_at: datetime


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resource: str
    action: str
    description: str | None


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
