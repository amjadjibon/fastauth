from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from fastauth.models import (
    Role,
    RoleCreate,
    RolePermission,
    RoleUpdate,
    UserRole,
)


async def create_role(session: AsyncSession, role_create: RoleCreate) -> Role:
    """Create a new role with optional permissions."""
    role_data = role_create.model_dump(exclude={"permission_ids"})
    role = Role(**role_data)

    session.add(role)
    await session.commit()
    await session.refresh(role)

    # Add permissions if provided
    if role_create.permission_ids:
        await assign_permissions_to_role(session, role.id, role_create.permission_ids)

    # Return role with permissions loaded
    return await get_role(session, role.id)


async def get_role(session: AsyncSession, role_id: int) -> Role | None:
    """Get role by ID with permissions."""
    result = await session.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    return result.scalar_one_or_none()


async def get_role_by_name(session: AsyncSession, name: str) -> Role | None:
    """Get role by name with permissions."""
    result = await session.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.name == name)
    )
    return result.scalar_one_or_none()


async def get_roles(
    session: AsyncSession, skip: int = 0, limit: int = 100, active_only: bool = True
) -> list[Role]:
    """Get all roles with permissions."""
    query = select(Role).options(selectinload(Role.permissions))

    if active_only:
        query = query.where(Role.is_active == True)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def update_role(
    session: AsyncSession, role_id: int, role_update: RoleUpdate
) -> Role | None:
    """Update role."""
    role = await get_role(session, role_id)
    if not role:
        return None

    update_data = role_update.model_dump(exclude_unset=True, exclude={"permission_ids"})

    for field, value in update_data.items():
        setattr(role, field, value)

    # Update permissions if provided
    if role_update.permission_ids is not None:
        await assign_permissions_to_role(session, role_id, role_update.permission_ids)

    await session.commit()

    # Return role with permissions loaded
    return await get_role(session, role_id)


async def delete_role(session: AsyncSession, role_id: int) -> bool:
    """Delete role and its associations."""
    role = await get_role(session, role_id)
    if not role:
        return False

    # Remove role-permission associations
    result = await session.execute(
        select(RolePermission).where(RolePermission.role_id == role_id)
    )
    role_permission_links = result.scalars().all()

    for link in role_permission_links:
        await session.delete(link)

    # Remove user-role associations
    result = await session.execute(select(UserRole).where(UserRole.role_id == role_id))
    user_role_links = result.scalars().all()

    for link in user_role_links:
        await session.delete(link)

    await session.delete(role)
    await session.commit()
    return True


async def assign_permissions_to_role(
    session: AsyncSession, role_id: int, permission_ids: list[int]
) -> bool:
    """Assign permissions to a role."""
    # Remove existing permissions
    result = await session.execute(
        select(RolePermission).where(RolePermission.role_id == role_id)
    )
    existing_links = result.scalars().all()

    for link in existing_links:
        await session.delete(link)

    # Add new permissions
    for permission_id in permission_ids:
        link = RolePermission(role_id=role_id, permission_id=permission_id)
        session.add(link)

    await session.commit()
    return True


async def get_role_permissions(session: AsyncSession, role_id: int) -> list:
    """Get all permissions for a role."""
    role = await get_role(session, role_id)
    if not role:
        return []

    return list(role.permissions)


async def get_role_count(session: AsyncSession) -> int:
    """Get total role count."""
    result = await session.execute(select(Role.id))
    return len(result.scalars().all())


async def search_roles(
    session: AsyncSession,
    query: str,
    skip: int = 0,
    limit: int = 100,
) -> list[Role]:
    """Search roles by name or description."""
    search_query = (
        select(Role)
        .options(selectinload(Role.permissions))
        .where((Role.name.contains(query)) | (Role.description.contains(query)))
        .offset(skip)
        .limit(limit)
    )

    result = await session.execute(search_query)
    return result.scalars().all()
