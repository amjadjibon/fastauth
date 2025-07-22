from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from .role_permissions import RolePermissionLink
from .user_roles import UserRoleLink

if TYPE_CHECKING:
    from .user import User
    from .permission import Permission, PermissionResponse


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
        link_model=UserRoleLink
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
