from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.repositories import user_repository as user_repo
from app.core.security import hash_password, verify_password


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User | None:
    user = await user_repo.find_by_username(session, username)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def register_user(session: AsyncSession, username: str, email: str, password: str) -> User:
    return await user_repo.create(session, username=username, email=email, password=password)


async def change_password(session: AsyncSession, user: User, new_password: str) -> User:
    user.hashed_password = hash_password(new_password)
    return await user_repo.update(session, user)
