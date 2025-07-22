from fastapi import FastAPI

from fastauth.api.auth import router as auth_router
from fastauth.api.health import router as health_router
from fastauth.api.permissions import router as permissions_router
from fastauth.api.rbac import router as rbac_router
from fastauth.api.roles import router as roles_router
from fastauth.api.users import router as users_router


def setup_routers(app: FastAPI):
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    app.include_router(roles_router, prefix="/api/v1/roles", tags=["roles"])
    app.include_router(permissions_router, prefix="/api/v1/permissions", tags=["permissions"])
    app.include_router(rbac_router, prefix="/api/v1/rbac", tags=["rbac"])
    app.include_router(health_router, prefix="/health", tags=["health"])
