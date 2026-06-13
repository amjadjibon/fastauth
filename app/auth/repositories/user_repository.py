from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.security import hash_password


async def find_by_id(session: AsyncSession, user_id: str) -> User | None:
    return await session.get(User, user_id)


async def find_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.exec(select(User).where(User.username == username))
    return result.first()


async def find_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.exec(select(User).where(User.email == email))
    return result.first()


async def create(session: AsyncSession, username: str, email: str, password: str, email_verified: bool = False) -> User:
    user = User(username=username, email=email, hashed_password=hash_password(password), email_verified=email_verified)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_no_commit(session: AsyncSession, username: str, email: str, password: str, email_verified: bool = False) -> User:
    """Stage a new user without committing — caller is responsible for commit."""
    user = User(username=username, email=email, hashed_password=hash_password(password), email_verified=email_verified)
    session.add(user)
    return user


async def update(session: AsyncSession, user: User) -> User:
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def delete(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    await session.commit()
