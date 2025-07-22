from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastauth.core.deps import require_role_update, require_user_read
from fastauth.crud.rbac import (
    assign_roles_to_user,
    get_user_permissions,
    user_has_permission,
)
from fastauth.db.session import get_session
from fastauth.models import (
    PermissionResponse,
    User,
)

router = APIRouter()


# User role management endpoints
@router.post("/users/{user_id}/roles", dependencies=[Depends(require_role_update)])
async def assign_roles_to_user_endpoint(
    user_id: int,
    role_ids: List[int],
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Assign roles to user."""
    await assign_roles_to_user(session, user_id, role_ids)
    return {"message": "Roles assigned successfully"}


@router.get("/users/{user_id}/permissions", response_model=List[PermissionResponse])
async def get_user_permissions_endpoint(
    user_id: int,
    current_user: User = Depends(require_user_read),
    session: AsyncSession = Depends(get_session),
) -> List[PermissionResponse]:
    """Get all permissions for a user."""
    # Users can view their own permissions, others need permission
    if current_user.id != user_id and not current_user.is_superuser:
        has_permission = await user_has_permission(session, current_user.id, "user", "read")
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    permissions = await get_user_permissions(session, user_id)
    return [PermissionResponse.model_validate(permission) for permission in permissions]


@router.get("/users/{user_id}/check-permission")
async def check_user_permission_endpoint(
    user_id: int,
    resource: str,
    action: str,
    current_user: User = Depends(require_user_read),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Check if user has specific permission."""
    # Users can check their own permissions, others need permission
    if current_user.id != user_id and not current_user.is_superuser:
        has_permission = await user_has_permission(session, current_user.id, "user", "read")
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    has_permission = await user_has_permission(session, user_id, resource, action)
    return {
        "user_id": user_id,
        "resource": resource,
        "action": action,
        "has_permission": has_permission
    }