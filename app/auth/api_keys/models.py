from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel


@dataclass
class APIKeyPrincipal:
    key_id: str
    owner_user_id: str
    scopes: list[str] = field(default_factory=list)


class CreateAPIKeyRequest(BaseModel):
    name: str
    scopes: list[str] = []
    expires_at: datetime | None = None


class CreateAPIKeyResponse(BaseModel):
    id: str
    name: str
    key: str  # raw key — shown once only


class APIKeyResponse(BaseModel):
    id: str
    name: str
    scopes: list[str]
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None
