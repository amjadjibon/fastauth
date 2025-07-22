from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastauth.core.deps import (
    require_permission_create,
    require_permission_delete,
    require_permission_read,
    require_permission_update,
)
from fastauth.crud.permission import (
    create_permission,
    delete_permission,
    get_permission,
    get_permission_by_name,
    get_permissions,
    update_permission,
)
from fastauth.db.session import get_session
from fastauth.models import (
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
)

router = APIRouter()


@router.post(
    "/",
    response_model=PermissionResponse,
    dependencies=[Depends(require_permission_create)],
)
async def create_permission_endpoint(
    permission_create: PermissionCreate,
    session: AsyncSession = Depends(get_session),
) -> PermissionResponse:
    """Create a new permission."""
    # Check if permission already exists
    existing_permission = await get_permission_by_name(session, permission_create.name)
    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission with this name already exists",
        )

    permission = await create_permission(session, permission_create)
    return PermissionResponse.model_validate(permission)


@router.get(
    "/",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_permission_read)],
)
async def get_permissions_endpoint(
    skip: int = 0,
    limit: int = 100,
    resource: str | None = None,
    action: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[PermissionResponse]:
    """Get all permissions with optional filtering."""
    permissions = await get_permissions(
        session, skip=skip, limit=limit, resource=resource, action=action
    )
    return [PermissionResponse.model_validate(permission) for permission in permissions]


@router.get("/resources", dependencies=[Depends(require_permission_read)])
async def get_permission_resources_endpoint(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get all unique resources."""
    from ..crud.permission import get_unique_resources

    resources = await get_unique_resources(session)
    return {"resources": list(resources)}


@router.get("/actions", dependencies=[Depends(require_permission_read)])
async def get_permission_actions_endpoint(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get all unique actions."""
    from ..crud.permission import get_unique_actions

    actions = await get_unique_actions(session)
    return {"actions": list(actions)}


@router.get(
    "/{permission_id}",
    response_model=PermissionResponse,
    dependencies=[Depends(require_permission_read)],
)
async def get_permission_endpoint(
    permission_id: int,
    session: AsyncSession = Depends(get_session),
) -> PermissionResponse:
    """Get permission by ID."""
    permission = await get_permission(session, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )
    return PermissionResponse.model_validate(permission)


@router.put(
    "/{permission_id}",
    response_model=PermissionResponse,
    dependencies=[Depends(require_permission_update)],
)
async def update_permission_endpoint(
    permission_id: int,
    permission_update: PermissionUpdate,
    session: AsyncSession = Depends(get_session),
) -> PermissionResponse:
    """Update permission."""
    permission = await update_permission(session, permission_id, permission_update)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )
    return PermissionResponse.model_validate(permission)


@router.delete("/{permission_id}", dependencies=[Depends(require_permission_delete)])
async def delete_permission_endpoint(
    permission_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete permission."""
    success = await delete_permission(session, permission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )
    return {"message": "Permission deleted successfully"}


@router.get(
    "/by-resource/{resource}",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_permission_read)],
)
async def get_permissions_by_resource_endpoint(
    resource: str,
    session: AsyncSession = Depends(get_session),
) -> list[PermissionResponse]:
    """Get all permissions for a specific resource."""
    from ..crud.permission import get_permissions_by_resource

    permissions = await get_permissions_by_resource(session, resource)
    return [PermissionResponse.model_validate(permission) for permission in permissions]


@router.get(
    "/by-action/{action}",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_permission_read)],
)
async def get_permissions_by_action_endpoint(
    action: str,
    session: AsyncSession = Depends(get_session),
) -> list[PermissionResponse]:
    """Get all permissions for a specific action."""
    from ..crud.permission import get_permissions_by_action

    permissions = await get_permissions_by_action(session, action)
    return [PermissionResponse.model_validate(permission) for permission in permissions]
