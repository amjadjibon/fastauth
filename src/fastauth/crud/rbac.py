from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from fastauth.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)


# User role management
async def assign_roles_to_user(
    session: AsyncSession, user_id: int, role_ids: List[int]
) -> bool:
    """Assign roles to a user."""
    # Remove existing roles
    result = await session.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    existing_links = result.scalars().all()
    
    for link in existing_links:
        await session.delete(link)
    
    # Add new roles
    for role_id in role_ids:
        link = UserRole(user_id=user_id, role_id=role_id)
        session.add(link)
    
    await session.commit()
    return True


async def get_user_roles(session: AsyncSession, user_id: int) -> List[Role]:
    """Get all roles for a user."""
    result = await session.execute(
        select(Role)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
        .where(Role.is_active == True)
    )
    return result.scalars().all()


async def get_user_permissions(session: AsyncSession, user_id: int) -> List[Permission]:
    """Get all permissions for a user through their roles."""
    result = await session.execute(
        select(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
        .where(Role.is_active == True)
        .distinct()
    )
    return result.scalars().all()


async def user_has_permission(
    session: AsyncSession, user_id: int, resource: str, action: str
) -> bool:
    """Check if user has a specific permission."""
    # First check if user is superuser
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if user and user.is_superuser:
        return True
    
    # Check specific permission
    result = await session.execute(
        select(Permission.id)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
        .where(Permission.resource == resource)
        .where(Permission.action == action)
        .where(Role.is_active == True)
        .limit(1)
    )
    
    return result.scalar_one_or_none() is not None


async def user_has_role(session: AsyncSession, user_id: int, role_name: str) -> bool:
    """Check if user has a specific role."""
    result = await session.execute(
        select(Role.id)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
        .where(Role.name == role_name)
        .where(Role.is_active == True)
        .limit(1)
    )
    
    return result.scalar_one_or_none() is not None


async def add_role_to_user(session: AsyncSession, user_id: int, role_id: int) -> bool:
    """Add a single role to a user."""
    # Check if user already has this role
    existing_result = await session.execute(
        select(UserRole).where(
            (UserRole.user_id == user_id) & 
            (UserRole.role_id == role_id)
        )
    )
    
    if existing_result.scalar_one_or_none():
        return True  # Already has the role
    
    # Add the role
    link = UserRole(user_id=user_id, role_id=role_id)
    session.add(link)
    await session.commit()
    return True


async def remove_role_from_user(session: AsyncSession, user_id: int, role_id: int) -> bool:
    """Remove a single role from a user."""
    result = await session.execute(
        select(UserRole).where(
            (UserRole.user_id == user_id) & 
            (UserRole.role_id == role_id)
        )
    )
    
    link = result.scalar_one_or_none()
    if not link:
        return False
    
    await session.delete(link)
    await session.commit()
    return True


async def get_users_with_role(session: AsyncSession, role_id: int) -> List[User]:
    """Get all users that have a specific role."""
    result = await session.execute(
        select(User)
        .join(UserRole, User.id == UserRole.user_id)
        .where(UserRole.role_id == role_id)
    )
    return result.scalars().all()


async def get_users_with_permission(
    session: AsyncSession, resource: str, action: str
) -> List[User]:
    """Get all users that have a specific permission."""
    result = await session.execute(
        select(User)
        .join(UserRole, User.id == UserRole.user_id)
        .join(Role, UserRole.role_id == Role.id)
        .join(RolePermission, Role.id == RolePermission.role_id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(Permission.resource == resource)
        .where(Permission.action == action)
        .where(Role.is_active == True)
        .distinct()
    )
    
    # Also include superusers
    superuser_result = await session.execute(
        select(User).where(User.is_superuser == True)
    )
    
    regular_users = result.scalars().all()
    superusers = superuser_result.scalars().all()
    
    # Combine and deduplicate
    all_users = {user.id: user for user in regular_users + superusers}
    return list(all_users.values())
