from fastauth.models.user import (
    User,
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    UserRoleLink,
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
    RolePermissionLink,
    RoleResponse,
    RoleUpdate,
)

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
    "UserRoleLink",
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
    "RolePermissionLink",
    "RoleResponse",
    "RoleUpdate",
]
