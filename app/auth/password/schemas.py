from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ChangePasswordRequest(BaseModel):
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


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"email": "alice@example.com"}})

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"token": "reset-token-example", "new_password": "NewP@ssw0rd!"}})

    token: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("password must contain at least one digit")
        return v
