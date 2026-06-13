from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import repositories as repo
from app.auth.models import User
from app.core.security import hash_password, verify_password


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User | None:
    user = await repo.user.find_by_username(session, username)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def register_user(session: AsyncSession, username: str, email: str, password: str) -> User:
    return await repo.user.create(session, username=username, email=email, password=password)


async def change_password(session: AsyncSession, user: User, new_password: str) -> User:
    user.hashed_password = hash_password(new_password)
    return await repo.user.update(session, user)
