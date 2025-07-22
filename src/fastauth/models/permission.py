from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel

# Forward references - will be resolved when importing other models
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fastauth.models.role import Role, RolePermissionLink


# Core Models
class PermissionBase(SQLModel):
    """Base permission model with common fields."""
    name: str = Field(unique=True, index=True, max_length=100)
    description: Optional[str] = Field(max_length=255)
    resource: str = Field(max_length=50)  # e.g., "user", "role", "permission"
    action: str = Field(max_length=50)    # e.g., "create", "read", "update", "delete"


class Permission(PermissionBase, table=True):
    """Permission database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    
    # Relationships
    roles: List["Role"] = Relationship(
        back_populates="permissions", 
        link_model="RolePermissionLink"
    )


# Request/Response Models
class PermissionCreate(PermissionBase):
    """Permission creation model."""
    pass


class PermissionUpdate(SQLModel):
    """Permission update model."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    resource: Optional[str] = Field(None, max_length=50)
    action: Optional[str] = Field(None, max_length=50)


class PermissionResponse(PermissionBase):
    """Permission response model."""
    id: int
    created_at: datetime
