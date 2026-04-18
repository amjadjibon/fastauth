from fastapi import APIRouter, HTTPException, status
from jose import JWTError

from app.auth import store
from app.auth.deps import CurrentUser, SessionDep, make_tokens
from app.auth.models import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.core.security import decode_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: SessionDep):
    if await store.username_exists(session, body.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    user = await store.create_user(session, body.username, body.email, body.password)
    access, refresh = make_tokens(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: SessionDep):
    user = await store.get_by_username(session, body.username)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access, refresh = make_tokens(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: SessionDep):
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = await store.get_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access, new_refresh = make_tokens(user.id)
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser):
    return UserResponse.model_validate(current_user)
