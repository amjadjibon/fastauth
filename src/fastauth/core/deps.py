from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from fastauth.core.security import (
    extract_user_permissions,
    extract_user_roles,
    user_has_permission_in_token,
    user_has_role_in_token,
    verify_token,
)
from fastauth.crud.user import get_user_by_id
from fastauth.db.session import get_session
from fastauth.models import User, UserStatus

security = HTTPBearer()


class TokenUser:
    """User object with token payload for optimized access."""

    def __init__(self, user: User, token_payload: dict):
        self.user = user
        self.token_payload = token_payload
        # Expose user attributes directly
        for attr in [
            "id",
            "email",
            "is_active",
            "is_superuser",
            "status",
            "first_name",
            "last_name",
        ]:
            setattr(self, attr, getattr(user, attr))

    @property
    def roles(self) -> list[str]:
        return extract_user_roles(self.token_payload)

    @property
    def permissions(self) -> list[dict]:
        return extract_user_permissions(self.token_payload)

    def has_permission(self, resource: str, action: str) -> bool:
        return user_has_permission_in_token(self.token_payload, resource, action)

    def has_role(self, role_name: str) -> bool:
        return user_has_role_in_token(self.token_payload, role_name)


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenUser:
    """Get current authenticated user with token data."""
    token = credentials.credentials
    payload = verify_token(token, "access")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_id(session, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive or suspended",
        )

    return TokenUser(user, payload)


async def get_current_active_user(
    current_user: TokenUser = Depends(get_current_user),
) -> TokenUser:
    """Get current active user."""
    return current_user


async def get_current_superuser(
    current_user: TokenUser = Depends(get_current_user),
) -> TokenUser:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions - superuser required",
        )
    return current_user


def require_permission(resource: str, action: str):
    """Dependency to require specific permission using token data."""

    async def permission_checker(
        current_user: TokenUser = Depends(get_current_user),
    ) -> TokenUser:
        # Check permission from token
        if not current_user.has_permission(resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions - {action} {resource} required",
            )

        return current_user

    return permission_checker


def require_any_permission(permissions: list[tuple[str, str]]):
    """Dependency to require any of the specified permissions using token data."""

    async def permission_checker(
        current_user: TokenUser = Depends(get_current_user),
    ) -> TokenUser:
        # Check if user has any of the required permissions
        for resource, action in permissions:
            if current_user.has_permission(resource, action):
                return current_user

        permission_names = [f"{action} {resource}" for resource, action in permissions]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions - one of [{', '.join(permission_names)}] required",
        )

    return permission_checker


def require_all_permissions(permissions: list[tuple[str, str]]):
    """Dependency to require all of the specified permissions using token data."""

    async def permission_checker(
        current_user: TokenUser = Depends(get_current_user),
    ) -> TokenUser:
        # Check if user has all required permissions
        for resource, action in permissions:
            if not current_user.has_permission(resource, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions - {action} {resource} required",
                )

        return current_user

    return permission_checker


# Common permission dependencies
require_user_read = require_permission("user", "read")
require_user_create = require_permission("user", "create")
require_user_update = require_permission("user", "update")
require_user_delete = require_permission("user", "delete")

require_role_read = require_permission("role", "read")
require_role_create = require_permission("role", "create")
require_role_update = require_permission("role", "update")
require_role_delete = require_permission("role", "delete")

require_permission_read = require_permission("permission", "read")
require_permission_create = require_permission("permission", "create")
require_permission_update = require_permission("permission", "update")
require_permission_delete = require_permission("permission", "delete")

# Admin-level permissions (can read/write users and roles)
require_admin_permissions = require_all_permissions(
    [
        ("user", "read"),
        ("user", "create"),
        ("user", "update"),
        ("role", "read"),
        ("role", "create"),
        ("role", "update"),
    ]
)

# Moderator-level permissions (can read users and basic management)
require_moderator_permissions = require_all_permissions(
    [
        ("user", "read"),
        ("user", "update"),
    ]
)


# Self-management permission (users can manage their own data)
def require_self_or_permission(resource: str, action: str):
    """Allow users to access their own data or require permission for others."""

    async def permission_checker(
        target_user_id: int,
        current_user: TokenUser = Depends(get_current_user),
    ) -> TokenUser:
        # Allow users to access their own data
        if current_user.id == target_user_id:
            return current_user

        # Check specific permission for other users
        if not current_user.has_permission(resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions - {action} {resource} required",
            )

        return current_user

    return permission_checker
