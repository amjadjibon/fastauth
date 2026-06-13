from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra={"example": {
        "id": "00000000-0000-0000-0000-000000000002",
        "name": "editor",
        "description": "Can read and write content",
        "is_system": False,
        "created_at": "2024-01-01T00:00:00Z",
    }})

    id: str
    name: str
    description: str | None
    is_system: bool
    created_at: datetime


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra={"example": {
        "id": "00000000-0000-0000-0000-000000000010",
        "resource": "posts",
        "action": "write",
        "description": "Create and update posts",
    }})

    id: str
    resource: str
    action: str
    description: str | None


class CreateRoleRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"name": "editor", "description": "Can read and write content"}})

    name: str
    description: str | None = None


class UpdateRoleRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"name": "senior-editor", "description": "Can also publish"}})

    name: str | None = None
    description: str | None = None


class AssignPermissionRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"permission_id": "00000000-0000-0000-0000-000000000010"}})

    permission_id: str


class AssignRoleRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"role_id": "00000000-0000-0000-0000-000000000002"}})

    role_id: str
