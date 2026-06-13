from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

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
    result = await session.exec(
        select(Permission).where(Permission.resource == resource, Permission.action == action)
    )
    return result.first()


async def list_all(session: AsyncSession) -> list[Permission]:
    result = await session.exec(select(Permission))
    return list(result.all())


async def assign_to_role(session: AsyncSession, role_id: str, permission_id: str) -> RolePermission:
    existing = await session.exec(
        select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
        )
    )
    if existing.first():
        raise ValueError("Role already has this permission")
    rp = RolePermission(role_id=role_id, permission_id=permission_id)
    session.add(rp)
    await session.commit()
    await session.refresh(rp)
    return rp


async def remove_from_role(session: AsyncSession, role_id: str, permission_id: str) -> bool:
    result = await session.exec(
        select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
        )
    )
    rp = result.first()
    if rp is None:
        return False
    await session.delete(rp)
    await session.commit()
    return True
