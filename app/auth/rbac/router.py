from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.auth.models import Permission, Role
from app.auth.deps import CurrentUser, SessionDep
from app.auth.rbac.dependencies import RequireRoles
from app.auth.rbac.models import (
    AssignPermissionRequest,
    AssignRoleRequest,
    CreateRoleRequest,
    PermissionResponse,
    RoleResponse,
    UpdateRoleRequest,
)
from app.auth.rbac.repositories import permission_repository, role_repository

router = APIRouter(prefix="/auth/roles", tags=["rbac"])


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[RequireRoles(["admin"])],
)
async def create_role(body: CreateRoleRequest, session: SessionDep):
    existing = await role_repository.find_by_name(session, body.name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")
    return await role_repository.create(session, body.name, body.description)


@router.get("", response_model=list[RoleResponse])
async def list_roles(session: SessionDep):
    result = await session.execute(select(Role))
    return list(result.scalars().all())


@router.patch("/{role_id}", response_model=RoleResponse, dependencies=[RequireRoles(["admin"])])
async def update_role(role_id: str, body: UpdateRoleRequest, session: SessionDep):
    role = await session.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify system roles"
        )
    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    return await role_repository.update(session, role)


@router.delete(
    "/{role_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[RequireRoles(["admin"])]
)
async def delete_role(role_id: str, session: SessionDep):
    role = await session.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete system roles"
        )
    await role_repository.delete(session, role)


@router.post("/{role_id}/permissions", dependencies=[RequireRoles(["admin"])])
async def assign_permission_to_role(
    role_id: str, body: AssignPermissionRequest, session: SessionDep
):
    role = await session.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    perm = await session.get(Permission, body.permission_id)
    if perm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    try:
        await permission_repository.assign_to_role(session, role_id, body.permission_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"message": "Permission assigned"}


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(session: SessionDep):
    return await permission_repository.list_all(session)


@router.post("/users/{user_id}/assign", dependencies=[RequireRoles(["admin"])])
async def assign_role_to_user(
    user_id: str, body: AssignRoleRequest, session: SessionDep, current_user: CurrentUser
):
    try:
        await role_repository.assign_to_user(
            session, user_id, body.role_id, assigned_by=current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"message": "Role assigned"}


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[RequireRoles(["admin"])],
)
async def remove_role_from_user(user_id: str, role_id: str, session: SessionDep):
    removed = await role_repository.remove_from_user(session, user_id, role_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User role not found")
