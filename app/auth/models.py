import uuid
from datetime import datetime, timezone

from pydantic import EmailStr, field_validator
from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- DB table ---

class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), sa_column=Column(String(36), primary_key=True))
    username: str = Field(sa_column=Column(String(32), unique=True, index=True))
    email: str = Field(sa_column=Column(String(254), unique=True))
    hashed_password: str = Field(sa_column=Column(String(60)))
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# --- Request models ---

class RegisterRequest(SQLModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("username may only contain letters, numbers, hyphens and underscores")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("password must contain at least one digit")
        return v


class LoginRequest(SQLModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(SQLModel):
    refresh_token: str = Field(min_length=1)


# --- Response models ---

class TokenResponse(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(SQLModel):
    id: str
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
