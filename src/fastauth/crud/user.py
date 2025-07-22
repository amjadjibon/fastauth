from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from fastauth.core.security import get_password_hash, verify_password
from fastauth.models import User, UserCreate, UserStatus, UserUpdate
from fastauth.crud.rbac import assign_roles_to_user


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """Get user by email with roles."""
    result = await session.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID with roles."""
    result = await session.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_users(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[UserStatus] = None,
    is_active: Optional[bool] = None,
    is_superuser: Optional[bool] = None,
) -> List[User]:
    """Get all users with optional filtering."""
    query = select(User).options(selectinload(User.roles))
    
    if status:
        query = query.where(User.status == status)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if is_superuser is not None:
        query = query.where(User.is_superuser == is_superuser)
    
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def create_user(session: AsyncSession, user_create: UserCreate) -> User:
    """Create a new user with optional roles."""
    hashed_password = get_password_hash(user_create.password)
    
    user_data = user_create.model_dump(exclude={"password", "role_ids"})
    user = User(
        **user_data,
        hashed_password=hashed_password,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    # Assign roles if provided
    if user_create.role_ids:
        await assign_roles_to_user(session, user.id, user_create.role_ids)
        await session.refresh(user)
    
    return user


async def update_user(
    session: AsyncSession, user_id: int, user_update: UserUpdate
) -> Optional[User]:
    """Update user."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True, exclude={"role_ids"})
    update_data["updated_at"] = datetime.now()
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    # Update roles if provided
    if user_update.role_ids is not None:
        await assign_roles_to_user(session, user_id, user_update.role_ids)
    
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_password(
    session: AsyncSession, user_id: int, new_password: str
) -> bool:
    """Update user password."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False
    
    user.hashed_password = get_password_hash(new_password)
    user.updated_at = datetime.now()
    
    await session.commit()
    return True


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    """Delete user and remove all role associations."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False
    
    # Role associations will be automatically removed due to cascade
    await session.delete(user)
    await session.commit()
    return True


async def activate_user(session: AsyncSession, user_id: int) -> bool:
    """Activate user account."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False
    
    user.is_active = True
    user.status = UserStatus.ACTIVE
    user.updated_at = datetime.now()
    
    await session.commit()
    return True


async def deactivate_user(session: AsyncSession, user_id: int) -> bool:
    """Deactivate user account."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False
    
    user.is_active = False
    user.status = UserStatus.INACTIVE
    user.updated_at = datetime.now()
    
    await session.commit()
    return True


async def suspend_user(session: AsyncSession, user_id: int) -> bool:
    """Suspend user account."""
    user = await get_user_by_id(session, user_id)
    if not user:
        return False
    
    user.is_active = False
    user.status = UserStatus.SUSPENDED
    user.updated_at = datetime.now()
    
    await session.commit()
    return True


async def authenticate_user(session: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password."""
    user = await get_user_by_email(session, email)
    if not user:
        return None
    if not user.is_active:
        return None
    if user.status != UserStatus.ACTIVE:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_count(session: AsyncSession) -> int:
    """Get total user count."""
    result = await session.execute(select(User.id))
    return len(result.scalars().all())


async def search_users(
    session: AsyncSession,
    query: str,
    skip: int = 0,
    limit: int = 100,
) -> List[User]:
    """Search users by email, first name, or last name."""
    search_query = select(User).options(selectinload(User.roles)).where(
        (User.email.contains(query)) |
        (User.first_name.contains(query)) |
        (User.last_name.contains(query))
    ).offset(skip).limit(limit)
    
    result = await session.execute(search_query)
    return result.scalars().all()