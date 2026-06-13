from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.db_models import Permission, Role, RolePermission, UserRole


async def find_by_name(session: AsyncSession, name: str) -> Role | None:
    result = await session.exec(select(Role).where(Role.name == name))
    return result.first()


async def create(session: AsyncSession, name: str, description: str | None = None) -> Role:
    role = Role(name=name, description=description)
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role


async def update(session: AsyncSession, role: Role) -> Role:
    role.updated_at = datetime.now(UTC)
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role


async def delete(session: AsyncSession, role: Role) -> None:
    await session.delete(role)
    await session.commit()


async def assign_to_user(session: AsyncSession, user_id: str, role_id: str, assigned_by: str | None = None) -> UserRole:
    existing = await session.exec(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    if existing.first():
        raise ValueError("User already has this role")
    user_role = UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
    session.add(user_role)
    await session.commit()
    await session.refresh(user_role)
    return user_role


async def remove_from_user(session: AsyncSession, user_id: str, role_id: str) -> bool:
    result = await session.exec(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    user_role = result.first()
    if user_role is None:
        return False
    await session.delete(user_role)
    await session.commit()
    return True


async def get_user_roles(session: AsyncSession, user_id: str) -> list[Role]:
    result = await session.exec(
        select(Role).join(UserRole, Role.id == UserRole.role_id).where(UserRole.user_id == user_id)
    )
    return list(result.all())


async def get_user_permissions(session: AsyncSession, user_id: str) -> list[Permission]:
    result = await session.exec(
        select(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return list(result.all())
