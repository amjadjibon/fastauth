from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.auth.deps import CurrentUser, SessionDep
from app.auth.rbac.repositories import role_repository


def RequireRoles(roles: list[str]):
    """Dependency factory: user must have at least one of the listed roles."""
    async def _check(current_user: CurrentUser, session: SessionDep) -> None:
        user_roles = await role_repository.get_user_roles(session, current_user.id)
        role_names = {r.name for r in user_roles}
        if not any(r in role_names for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {roles}",
            )
    return Depends(_check)


def RequirePermissions(perms: list[str]):
    """Dependency factory: user must have all listed permissions (resource:action)."""
    async def _check(current_user: CurrentUser, session: SessionDep) -> None:
        user_perms = await role_repository.get_user_permissions(session, current_user.id)
        perm_keys = {f"{p.resource}:{p.action}" for p in user_perms}
        for required in perms:
            if required not in perm_keys:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{required}' required",
                )
    return Depends(_check)
