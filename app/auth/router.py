from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from pydantic import BaseModel

from app.auth import store
from app.auth.deps import CurrentUser, SessionDep, make_tokens
from app.auth.mfa.models import MfaLoginRequest
from app.auth.mfa.totp import verify_totp as _verify_totp
from app.auth.models import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.auth.services import mfa_service
from app.core.metrics import (
    auth_login_attempts_total,
    auth_registrations_total,
    auth_token_refreshes_total,
)
from app.core.ratelimit import RateLimiter
from app.core.security import create_token, decode_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_session_token: str | None = None


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def register(body: RegisterRequest, session: SessionDep):
    if await store.username_exists(session, body.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    user = await store.create_user(session, body.username, body.email, body.password)
    auth_registrations_total.inc()
    return RegisterResponse(user_id=user.id)


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def login(body: LoginRequest, session: SessionDep):
    from datetime import timedelta
    user = await store.get_by_username(session, body.username)
    if user is None or not verify_password(body.password, user.hashed_password):
        auth_login_attempts_total.labels(success="false").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    auth_login_attempts_total.labels(success="true").inc()

    if await mfa_service.is_mfa_enabled(session, user.id):
        # Issue a short-lived MFA session token; full tokens issued after TOTP
        mfa_token = create_token(
            {"sub": user.id, "type": "mfa_pending"},
            timedelta(minutes=5),
        )
        return LoginResponse(mfa_required=True, mfa_session_token=mfa_token)

    access, refresh = make_tokens(user.id)
    return LoginResponse(access_token=access, refresh_token=refresh)


@router.post(
    "/login/mfa",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def login_mfa(body: MfaLoginRequest, session: SessionDep):
    try:
        payload = decode_token(body.mfa_session_token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA session token") from exc

    if payload.get("type") != "mfa_pending":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    user = await store.get_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    mfa = await mfa_service.get_mfa_secret(session, user.id)
    if mfa is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not configured")

    if body.is_backup_code:
        ok = await mfa_service.verify_backup_code(session, user.id, body.code)
    else:
        ok = _verify_totp(mfa.secret_encrypted, body.code)

    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    access, refresh = make_tokens(user.id, amr=["pwd", "mfa"])
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter(times=20, seconds=60))],
)
async def refresh(body: RefreshRequest, session: SessionDep):
    try:
        payload = decode_token(body.refresh_token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = await store.get_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access, new_refresh = make_tokens(user.id)
    auth_token_refreshes_total.inc()
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser):
    return UserResponse.model_validate(current_user)
