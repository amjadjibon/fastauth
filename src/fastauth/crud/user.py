from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from fastauth.core.security import get_password_hash, verify_password
from fastauth.models.user import User, UserCreate


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_create: UserCreate) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(user_create.password)
    user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        is_active=user_create.is_active,
        role=user_create.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password."""
    user = await get_user_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user