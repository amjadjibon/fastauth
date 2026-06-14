from pydantic import BaseModel, ConfigDict, EmailStr, Field


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"token": "verify-token-example"}})

    token: str = Field(min_length=1, max_length=128)


class ResendVerificationRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"email": "alice@example.com"}})

    email: EmailStr
