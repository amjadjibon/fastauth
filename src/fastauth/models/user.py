from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"


class UserBase(SQLModel):
    """Base user model with common fields."""
    email: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    role: UserRole = UserRole.USER


class User(UserBase, table=True):
    """User database model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str


class UserCreate(UserBase):
    """User creation model."""
    password: str


class UserResponse(UserBase):
    """User response model."""
    id: int


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