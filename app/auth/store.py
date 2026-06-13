from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.security import hash_password


async def create_user(session: AsyncSession, username: str, email: str, password: str) -> User:
    user = User(username=username, email=email, hashed_password=hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.exec(select(User).where(User.username == username))
    return result.first()


async def get_by_id(session: AsyncSession, user_id: str) -> User | None:
    return await session.get(User, user_id)


async def username_exists(session: AsyncSession, username: str) -> bool:
    result = await session.exec(select(User.id).where(User.username == username))
    return result.first() is not None


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.exec(select(User).where(User.email == email))
    return result.first()
