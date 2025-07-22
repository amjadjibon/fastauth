from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from fastauth.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    data: dict[str, Any],
    roles: list[str] | None = None,
    permissions: list[dict[str, str]] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token with roles and permissions."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    # Add roles and permissions to token
    if roles:
        to_encode["roles"] = roles
    if permissions:
        to_encode["permissions"] = permissions

    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str, token_type: str = "access") -> dict[str, Any] | None:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None


def create_token_data(
    user_id: int, email: str, is_superuser: bool = False
) -> dict[str, Any]:
    """Create base token data dictionary."""
    return {
        "sub": str(user_id),
        "email": email,
        "is_superuser": is_superuser,
    }


def extract_user_roles(token_payload: dict[str, Any]) -> list[str]:
    """Extract user roles from token payload."""
    return token_payload.get("roles", [])


def extract_user_permissions(token_payload: dict[str, Any]) -> list[dict[str, str]]:
    """Extract user permissions from token payload."""
    return token_payload.get("permissions", [])


def user_has_permission_in_token(
    token_payload: dict[str, Any], resource: str, action: str
) -> bool:
    """Check if user has permission based on token data."""
    # Superuser has all permissions
    if token_payload.get("is_superuser", False):
        return True

    # Check permissions in token
    permissions = extract_user_permissions(token_payload)
    for perm in permissions:
        if perm.get("resource") == resource and perm.get("action") == action:
            return True

    return False


def user_has_role_in_token(token_payload: dict[str, Any], role_name: str) -> bool:
    """Check if user has role based on token data."""
    roles = extract_user_roles(token_payload)
    return role_name in roles


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)
