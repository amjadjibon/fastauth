from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.db_models import Permission, RolePermission


async def create(
    session: AsyncSession, resource: str, action: str, description: str | None = None
) -> Permission:
    perm = Permission(resource=resource, action=action, description=description)
    session.add(perm)
    await session.commit()
    await session.refresh(perm)
    return perm


async def find_by_resource_and_action(
    session: AsyncSession, resource: str, action: str
) -> Permission | None:
    result = await session.execute(
        select(Permission).where(Permission.resource == resource, Permission.action == action)
    )
    return result.scalar_one_or_none()


async def list_all(session: AsyncSession) -> list[Permission]:
    result = await session.execute(select(Permission))
    return list(result.scalars().all())


async def assign_to_role(session: AsyncSession, role_id: str, permission_id: str) -> RolePermission:
    existing = await session.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Role already has this permission")
    rp = RolePermission(role_id=role_id, permission_id=permission_id)
    session.add(rp)
    await session.commit()
    await session.refresh(rp)
    return rp


async def remove_from_role(session: AsyncSession, role_id: str, permission_id: str) -> bool:
    result = await session.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
        )
    )
    rp = result.scalar_one_or_none()
    if rp is None:
        return False
    await session.delete(rp)
    await session.commit()
    return True
