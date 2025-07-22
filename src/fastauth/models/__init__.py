from fastauth.models.user_role import UserRole
from fastauth.models.role_permission import RolePermission
from fastauth.models.user import (
    User,
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    UserStatus,
    UserUpdate,
    Token,
    TokenRefresh,
)
from fastauth.models.permission import (
    Permission,
    PermissionBase,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
)
from fastauth.models.role import (
    Role,
    RoleBase,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from fastauth.models.health import HealthResponse

UserResponse.model_rebuild()
RoleResponse.model_rebuild()
PermissionResponse.model_rebuild()

__all__ = [
    # User models
    "User",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserRole",
    "UserStatus",
    "UserUpdate",
    "Token",
    "TokenRefresh",

    # Permission models
    "Permission",
    "PermissionBase",
    "PermissionCreate",
    "PermissionResponse",
    "PermissionUpdate",

    # Role models
    "Role",
    "RoleBase",
    "RoleCreate",
    "RolePermission",
    "RoleResponse",
    "RoleUpdate",

    # Health models
    "HealthResponse",
]
