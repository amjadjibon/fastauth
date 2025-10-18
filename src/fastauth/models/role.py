from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from .role_permission import RolePermission
from .user_role import UserRole

if TYPE_CHECKING:
    from .permission import Permission, PermissionResponse
    from .user import User


class RoleBase(SQLModel):
    """Base role model with common fields."""

    name: str = Field(unique=True, index=True, max_length=50)
    description: str | None = Field(max_length=255)
    is_active: bool = True


class Role(RoleBase, table=True):
    """Role database model."""

    __tablename__ = "roles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    users: list["User"] = Relationship(back_populates="roles", link_model=UserRole)
    permissions: list["Permission"] = Relationship(
        back_populates="roles", link_model=RolePermission
    )


class RoleCreate(RoleBase):
    """Role creation model."""

    permission_ids: list[UUID] | None = []


class RoleUpdate(SQLModel):
    """Role update model."""

    name: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    permission_ids: list[UUID] | None = None


class RoleResponse(RoleBase):
    """Role response model."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    permissions: list["PermissionResponse"] = []
