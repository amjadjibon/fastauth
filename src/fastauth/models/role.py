from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


# Forward references - will be resolved when importing other models
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fastauth.models.user import User, UserRoleLink
    from fastauth.models.permission import Permission, PermissionResponse


# Association Table
class RolePermissionLink(SQLModel, table=True):
    """Association table for Role and Permission many-to-many relationship."""
    __tablename__ = "role_permissions"
    
    role_id: int = Field(foreign_key="role.id", primary_key=True)
    permission_id: int = Field(foreign_key="permission.id", primary_key=True)


# Core Models
class RoleBase(SQLModel):
    """Base role model with common fields."""
    name: str = Field(unique=True, index=True, max_length=50)
    description: Optional[str] = Field(max_length=255)
    is_active: bool = True


class Role(RoleBase, table=True):
    """Role database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    
    # Relationships
    users: List["User"] = Relationship(
        back_populates="roles", 
        link_model="UserRoleLink"
    )
    permissions: List["Permission"] = Relationship(
        back_populates="roles", 
        link_model=RolePermissionLink
    )


# Request/Response Models
class RoleCreate(RoleBase):
    """Role creation model."""
    permission_ids: Optional[List[int]] = []


class RoleUpdate(SQLModel):
    """Role update model."""
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None


class RoleResponse(RoleBase):
    """Role response model."""
    id: int
    created_at: datetime
    updated_at: datetime
    permissions: List["PermissionResponse"] = []
