from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastauth.core.deps import (
    require_role_create,
    require_role_delete,
    require_role_read,
    require_role_update,
)
from fastauth.crud.role import (
    assign_permissions_to_role,
    create_role,
    delete_role,
    get_role,
    get_role_by_name,
    get_roles,
    update_role,
)
from fastauth.db.session import get_session
from fastauth.models import (
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)

router = APIRouter()


@router.post("/", response_model=RoleResponse, dependencies=[Depends(require_role_create)])
async def create_role_endpoint(
    role_create: RoleCreate,
    session: AsyncSession = Depends(get_session),
) -> RoleResponse:
    """Create a new role."""
    # Check if role already exists
    existing_role = await get_role_by_name(session, role_create.name)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists"
        )
    
    role = await create_role(session, role_create)
    return RoleResponse.model_validate(role)


@router.get("/", response_model=List[RoleResponse], dependencies=[Depends(require_role_read)])
async def get_roles_endpoint(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    session: AsyncSession = Depends(get_session),
) -> List[RoleResponse]:
    """Get all roles."""
    roles = await get_roles(session, skip=skip, limit=limit, active_only=active_only)
    return [RoleResponse.model_validate(role) for role in roles]


@router.get("/{role_id}", response_model=RoleResponse, dependencies=[Depends(require_role_read)])
async def get_role_endpoint(
    role_id: int,
    session: AsyncSession = Depends(get_session),
) -> RoleResponse:
    """Get role by ID."""
    role = await get_role(session, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return RoleResponse.model_validate(role)


@router.put("/{role_id}", response_model=RoleResponse, dependencies=[Depends(require_role_update)])
async def update_role_endpoint(
    role_id: int,
    role_update: RoleUpdate,
    session: AsyncSession = Depends(get_session),
) -> RoleResponse:
    """Update role."""
    role = await update_role(session, role_id, role_update)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return RoleResponse.model_validate(role)


@router.delete("/{role_id}", dependencies=[Depends(require_role_delete)])
async def delete_role_endpoint(
    role_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete role."""
    success = await delete_role(session, role_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return {"message": "Role deleted successfully"}


@router.post("/{role_id}/permissions", dependencies=[Depends(require_role_update)])
async def assign_permissions_to_role_endpoint(
    role_id: int,
    permission_ids: List[int],
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Assign permissions to role."""
    role = await get_role(session, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    await assign_permissions_to_role(session, role_id, permission_ids)
    return {"message": "Permissions assigned successfully"}


@router.get("/{role_id}/permissions", response_model=List[dict], dependencies=[Depends(require_role_read)])
async def get_role_permissions_endpoint(
    role_id: int,
    session: AsyncSession = Depends(get_session),
) -> List[dict]:
    """Get all permissions for a role."""
    role = await get_role(session, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    from ..models import PermissionResponse
    return [PermissionResponse.model_validate(permission) for permission in role.permissions]