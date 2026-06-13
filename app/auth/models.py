import uuid
from datetime import UTC, datetime

from pydantic import ConfigDict, EmailStr, field_validator
from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel

_JWT_EXAMPLE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"


def _now() -> datetime:
    return datetime.now(UTC)


# --- DB table ---


class User(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    username: str = Field(sa_column=Column(String(32), unique=True, index=True))
    email: str = Field(sa_column=Column(String(254), unique=True))
    hashed_password: str = Field(sa_column=Column(String(60)))
    created_at: datetime = Field(
        default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


# --- Request models ---


class RegisterRequest(SQLModel):
    model_config = ConfigDict(json_schema_extra={"example": {"username": "alice", "email": "alice@example.com", "password": "MyP@ssw0rd!"}})

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
    model_config = ConfigDict(json_schema_extra={"example": {"username": "alice", "password": "MyP@ssw0rd!"}})

    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(SQLModel):
    model_config = ConfigDict(json_schema_extra={"example": {"refresh_token": _JWT_EXAMPLE}})

    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(SQLModel):
    model_config = ConfigDict(json_schema_extra={"example": {"current_password": "MyP@ssw0rd!", "new_password": "NewP@ssw0rd!"}})

    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("password must contain at least one digit")
        return v


class ForgotPasswordRequest(SQLModel):
    model_config = ConfigDict(json_schema_extra={"example": {"email": "alice@example.com"}})

    email: EmailStr


class ResetPasswordRequest(SQLModel):
    model_config = ConfigDict(json_schema_extra={"example": {"token": "reset-token-example", "new_password": "NewP@ssw0rd!"}})

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("password must contain at least one digit")
        return v


# --- Response models ---


class TokenResponse(SQLModel):
    model_config = ConfigDict(json_schema_extra={"example": {"access_token": _JWT_EXAMPLE, "refresh_token": _JWT_EXAMPLE, "token_type": "bearer"}})

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterResponse(SQLModel):
    model_config = ConfigDict(json_schema_extra={"example": {"user_id": "00000000-0000-0000-0000-000000000001"}})

    user_id: str


class UserResponse(SQLModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "alice",
        "email": "alice@example.com",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }})

    id: str
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
