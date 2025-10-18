from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from fastauth.models.role_permission import RolePermission

if TYPE_CHECKING:
    from fastauth.models.role import Role


class PermissionBase(SQLModel):
    """Base permission model with common fields."""

    name: str = Field(unique=True, index=True, max_length=100)
    description: str | None = Field(max_length=255)
    resource: str = Field(max_length=50)  # e.g., "user", "role", "permission"
    action: str = Field(max_length=50)  # e.g., "create", "read", "update", "delete"


class Permission(PermissionBase, table=True):
    """Permission database model."""

    __tablename__ = "permissions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    # Relationships
    roles: list["Role"] = Relationship(
        back_populates="permissions", link_model=RolePermission
    )


class PermissionCreate(PermissionBase):
    """Permission creation model."""

    pass


class PermissionUpdate(SQLModel):
    """Permission update model."""

    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=255)
    resource: str | None = Field(None, max_length=50)
    action: str | None = Field(None, max_length=50)


class PermissionResponse(PermissionBase):
    """Permission response model."""

    id: UUID
    created_at: datetime
