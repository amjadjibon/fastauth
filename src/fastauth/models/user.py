from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from fastauth.models.user_role import UserRole

if TYPE_CHECKING:
    from fastauth.models.role import Role, RoleResponse


class UserStatus(str, Enum):
    """User status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class UserBase(SQLModel):
    """Base user model with common fields."""

    email: str = Field(unique=True, index=True, max_length=255)
    first_name: str | None = Field(max_length=100)
    last_name: str | None = Field(max_length=100)
    is_active: bool = True
    is_superuser: bool = False
    status: UserStatus = UserStatus.ACTIVE


class User(UserBase, table=True):
    """User database model."""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    roles: list["Role"] = Relationship(back_populates="users", link_model=UserRole)


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(min_length=8)
    role_ids: list[UUID] | None = []


class UserUpdate(SQLModel):
    """User update model."""

    email: str | None = Field(None, max_length=255)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    is_active: bool | None = None
    is_superuser: bool | None = None
    status: UserStatus | None = None
    role_ids: list[UUID] | None = None


class UserResponse(UserBase):
    """User response model."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    roles: list["RoleResponse"] = []


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
