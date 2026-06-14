from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_JWT_EXAMPLE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"


class RegisterRequest(BaseModel):
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


class LoginRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"username": "alice", "password": "MyP@ssw0rd!"}})

    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"refresh_token": _JWT_EXAMPLE}})

    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"access_token": _JWT_EXAMPLE, "refresh_token": _JWT_EXAMPLE, "token_type": "bearer"}})

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"user_id": "00000000-0000-0000-0000-000000000001"}})

    user_id: str


class UserResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "alice",
        "email": "alice@example.com",
        "email_verified": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }})

    id: str
    username: str
    email: str
    email_verified: bool = False
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"access_token": _JWT_EXAMPLE, "refresh_token": _JWT_EXAMPLE, "token_type": "bearer", "mfa_required": False}})

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_session_token: str | None = None
