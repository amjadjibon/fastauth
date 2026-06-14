import hashlib
import secrets
from dataclasses import dataclass, field


@dataclass
class APIKeyPrincipal:
    key_id: str
    owner_user_id: str
    scopes: list[str] = field(default_factory=list)


def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, sha256_hash). Raw key shown once; only hash is stored."""
    raw = "fak_" + secrets.token_urlsafe(32)
    return raw, hash_api_key(raw)


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
