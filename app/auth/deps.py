from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import store
from app.auth.models import User
from app.core.config import settings
from app.core.db import get_session
from app.core.security import create_token, decode_token

bearer = HTTPBearer()


def make_tokens(user_id: str) -> tuple[str, str]:
    access = create_token(
        {"sub": user_id, "type": "access"},
        timedelta(seconds=settings.access_token_expire_seconds),
    )
    refresh = create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(seconds=settings.refresh_token_expire_seconds),
    )
    return access, refresh


async def get_current_user(credentials: BearerDep, session: SessionDep) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = await store.get_by_id(session, payload["sub"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


SessionDep = Annotated[AsyncSession, Depends(get_session)]
BearerDep = Annotated[HTTPAuthorizationCredentials, Depends(bearer)]
CurrentUser = Annotated[User, Depends(get_current_user)]
