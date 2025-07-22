from datetime import datetime
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from fastauth.models.user_roles import UserRoleLink

if TYPE_CHECKING:
    from fastauth.models.role import Role


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


# Core Models
class UserBase(SQLModel):
    """Base user model with common fields."""
    email: str = Field(unique=True, index=True, max_length=255)
    first_name: Optional[str] = Field(max_length=100)
    last_name: Optional[str] = Field(max_length=100)
    is_active: bool = True
    is_superuser: bool = False
    status: UserStatus = UserStatus.ACTIVE


class User(UserBase, table=True):
    """User database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    
    # Relationships
    roles: List["Role"] = Relationship(
        back_populates="users", 
        link_model=UserRoleLink
    )


# Request/Response Models
class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(min_length=8)
    role_ids: Optional[List[int]] = []


class UserUpdate(SQLModel):
    """User update model."""
    email: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    status: Optional[UserStatus] = None
    role_ids: Optional[List[int]] = None


class UserResponse(UserBase):
    """User response model."""
    id: int
    created_at: datetime
    updated_at: datetime
    roles: List["RoleResponse"] = []


# Authentication Models
class UserLogin(SQLModel):
    """User login model."""
    email: str
    password: str


class Token(SQLModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(SQLModel):
    """Token refresh model."""
    refresh_token: str
