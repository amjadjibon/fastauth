from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _rsa_private_key() -> str | None:
    if settings.algorithm == "RS256" and settings.rsa_private_key_path:
        with open(settings.rsa_private_key_path) as f:
            return f.read()
    return None


def _rsa_public_key() -> str | None:
    if settings.algorithm == "RS256" and settings.rsa_private_key_path:
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PublicFormat,
            load_pem_private_key,
        )

        with open(settings.rsa_private_key_path, "rb") as f:
            private_key = load_pem_private_key(f.read(), password=None)
        return (
            private_key.public_key()
            .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
            .decode()
        )
    return None


def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(UTC) + expires_delta
    key = _rsa_private_key() or settings.secret_key
    return jwt.encode(payload, key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    if settings.algorithm == "RS256":
        pub = _rsa_public_key()
        if pub:
            return jwt.decode(token, pub, algorithms=["RS256"])
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
