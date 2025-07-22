from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from fastauth.models import (
    Permission,
    PermissionCreate,
    PermissionUpdate,
    RolePermissionLink,
)


async def create_permission(session: AsyncSession, permission_create: PermissionCreate) -> Permission:
    """Create a new permission."""
    permission = Permission(**permission_create.model_dump())
    session.add(permission)
    await session.commit()
    await session.refresh(permission)
    return permission


async def get_permission(session: AsyncSession, permission_id: int) -> Optional[Permission]:
    """Get permission by ID."""
    result = await session.execute(select(Permission).where(Permission.id == permission_id))
    return result.scalar_one_or_none()


async def get_permission_by_name(session: AsyncSession, name: str) -> Optional[Permission]:
    """Get permission by name."""
    result = await session.execute(select(Permission).where(Permission.name == name))
    return result.scalar_one_or_none()


async def get_permissions(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    resource: Optional[str] = None,
    action: Optional[str] = None,
) -> List[Permission]:
    """Get all permissions with optional filtering."""
    query = select(Permission)
    
    if resource:
        query = query.where(Permission.resource == resource)
    if action:
        query = query.where(Permission.action == action)
    
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def update_permission(
    session: AsyncSession, permission_id: int, permission_update: PermissionUpdate
) -> Optional[Permission]:
    """Update permission."""
    permission = await get_permission(session, permission_id)
    if not permission:
        return None
    
    update_data = permission_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(permission, field, value)
    
    await session.commit()
    await session.refresh(permission)
    return permission


async def delete_permission(session: AsyncSession, permission_id: int) -> bool:
    """Delete permission and its associations."""
    permission = await get_permission(session, permission_id)
    if not permission:
        return False
    
    # Remove role-permission associations
    result = await session.execute(
        select(RolePermissionLink).where(RolePermissionLink.permission_id == permission_id)
    )
    links = result.scalars().all()
    
    for link in links:
        await session.delete(link)
    
    await session.delete(permission)
    await session.commit()
    return True


async def get_permissions_by_resource(
    session: AsyncSession,
    resource: str,
    skip: int = 0,
    limit: int = 100,
) -> List[Permission]:
    """Get all permissions for a specific resource."""
    result = await session.execute(
        select(Permission)
        .where(Permission.resource == resource)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_permissions_by_action(
    session: AsyncSession,
    action: str,
    skip: int = 0,
    limit: int = 100,
) -> List[Permission]:
    """Get all permissions for a specific action."""
    result = await session.execute(
        select(Permission)
        .where(Permission.action == action)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_unique_resources(session: AsyncSession) -> List[str]:
    """Get all unique resources."""
    from sqlmodel import distinct
    
    result = await session.execute(select(distinct(Permission.resource)))
    return result.scalars().all()


async def get_unique_actions(session: AsyncSession) -> List[str]:
    """Get all unique actions."""
    from sqlmodel import distinct
    
    result = await session.execute(select(distinct(Permission.action)))
    return result.scalars().all()


async def get_permission_count(session: AsyncSession) -> int:
    """Get total permission count."""
    result = await session.execute(select(Permission.id))
    return len(result.scalars().all())


async def search_permissions(
    session: AsyncSession,
    query: str,
    skip: int = 0,
    limit: int = 100,
) -> List[Permission]:
    """Search permissions by name, resource, action, or description."""
    search_query = select(Permission).where(
        (Permission.name.contains(query)) |
        (Permission.resource.contains(query)) |
        (Permission.action.contains(query)) |
        (Permission.description.contains(query))
    ).offset(skip).limit(limit)
    
    result = await session.execute(search_query)
    return result.scalars().all()


async def permission_exists(
    session: AsyncSession,
    resource: str,
    action: str,
    exclude_id: Optional[int] = None
) -> bool:
    """Check if permission with resource and action already exists."""
    query = select(Permission).where(
        (Permission.resource == resource) &
        (Permission.action == action)
    )
    
    if exclude_id:
        query = query.where(Permission.id != exclude_id)
    
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None