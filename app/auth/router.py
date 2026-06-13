from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from pydantic import BaseModel

from app.auth import store
from app.auth.audit.events import AuditEvent
from app.auth.audit.logger import audit_log as _audit
from app.auth.deps import BearerDep, CurrentUser, SessionDep
from app.auth.mfa.models import MfaLoginRequest
from app.auth.mfa.totp import verify_totp as _verify_totp
from app.auth.models import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.auth.security.brute_force import get_brute_force_protection
from app.auth.security.lockout import is_account_locked
from app.auth.services import mfa_service
from app.core.config import settings
from app.core.metrics import (
    auth_login_attempts_total,
    auth_registrations_total,
    auth_token_refreshes_total,
)
from app.core.ratelimit import RateLimiter
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.core.email import send_verification_email
from app.core.token_blocklist import block_token

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_verification_token(session, user) -> str:
    import hashlib
    import secrets
    from datetime import timedelta

    from app.auth.db_models import EmailVerificationToken

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    vtoken = EmailVerificationToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
    session.add(vtoken)
    await session.commit()
    await send_verification_email(user.id, user.email, raw_token)
    return raw_token


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
    responses={
        409: {"description": "Username or email already taken", "content": {"application/json": {"example": {"detail": "Username already taken"}}}},
        422: {"description": "Validation error (weak password, invalid email, etc.)"},
        429: {"description": "Rate limited"},
    },
)
async def register(body: RegisterRequest, session: SessionDep):
    if await store.username_exists(session, body.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    user = await store.create_user(session, body.username, body.email, body.password)
    auth_registrations_total.inc()
    await _issue_verification_token(session, user)
    await _audit(session, AuditEvent.EMAIL_VERIFICATION_SENT, user_id=user.id)
    return RegisterResponse(user_id=user.id)


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
    responses={
        401: {"description": "Invalid credentials", "content": {"application/json": {"example": {"detail": "Invalid credentials"}}}},
        429: {"description": "Rate limited or brute-force protection triggered", "content": {"application/json": {"example": {"detail": "Too many failed attempts. Try again later."}}}},
    },
)
async def login(body: LoginRequest, session: SessionDep, request: Request):
    from datetime import timedelta

    from app.auth.services import session_service as svc
    from app.auth.sessions.device_info import parse_user_agent
    from app.core.limiter import _redis  # use the shared redis instance if available

    ip = request.client.host if request.client else "unknown"
    bf = get_brute_force_protection(redis=_redis)

    if await bf.is_blocked(f"user:{body.username}") or await bf.is_blocked(f"ip:{ip}"):
        auth_login_attempts_total.labels(success="false").inc()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts, try again later",
        )

    user = await store.get_by_username(session, body.username)

    if user and await is_account_locked(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account locked")

    if user is None or not verify_password(body.password, user.hashed_password):
        await bf.check_and_record(body.username, ip)
        auth_login_attempts_total.labels(success="false").inc()
        await _audit(
            session,
            AuditEvent.LOGIN_FAILED,
            ip_address=ip,
            outcome="failure",
            metadata={"username": body.username},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Clear brute-force counter on successful login
    if _redis:
        await _redis.delete(f"bf:attempts:user:{body.username}", f"bf:attempts:ip:{ip}")

    if settings.require_email_verification and not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    auth_login_attempts_total.labels(success="true").inc()
    await _audit(session, AuditEvent.LOGIN_SUCCESS, user_id=user.id, ip_address=ip)

    if await mfa_service.is_mfa_enabled(session, user.id):
        # Issue a short-lived MFA session token; full tokens issued after TOTP
        mfa_token = create_token(
            {"sub": user.id, "type": "mfa_pending"},
            timedelta(minutes=5),
        )
        return LoginResponse(mfa_required=True, mfa_session_token=mfa_token)

    ua = request.headers.get("user-agent", "")
    device = parse_user_agent(request)
    access, refresh, _ = await svc.create_session(
        session,
        user_id=user.id,
        ip_address=ip,
        user_agent=ua,
        device_type=device.get("device_type"),
        device_name=device.get("device_name"),
        browser=device.get("browser"),
        os=device.get("os"),
    )
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA session token"
        ) from exc

    if payload.get("type") != "mfa_pending":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    user = await store.get_by_id(session, user_id)  # type: ignore
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    mfa = await mfa_service.get_mfa_secret(session, user.id)
    if mfa is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not configured")

    if body.is_backup_code:
        ok = await mfa_service.verify_backup_code(session, user.id, body.code)
    else:
        from app.core.encryption import decrypt as _decrypt

        ok = _verify_totp(_decrypt(mfa.secret_encrypted), body.code)

    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    from app.auth.services import session_service as svc

    access, refresh, _ = await svc.create_session(session, user_id=user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter(times=20, seconds=60))],
    responses={
        401: {"description": "Invalid or revoked refresh token", "content": {"application/json": {"example": {"detail": "Invalid or expired refresh token"}}}},
    },
)
async def refresh(body: RefreshRequest, session: SessionDep):
    from app.auth.services import session_service as svc

    result = await svc.refresh_session(session, body.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked refresh token"
        )
    access, refresh_token, _ = result
    auth_token_refreshes_total.inc()
    return TokenResponse(access_token=access, refresh_token=refresh_token)


@router.get("/me")
async def me(current_user: CurrentUser, session: SessionDep):
    from app.auth.rbac.repositories import role_repository

    roles = await role_repository.get_user_roles(session, current_user.id)
    perms = await role_repository.get_user_permissions(session, current_user.id)
    user_data = UserResponse.model_validate(current_user).model_dump()
    user_data["roles"] = [r.name for r in roles]
    user_data["permissions"] = [f"{p.resource}:{p.action}" for p in perms]
    return user_data


@router.post("/logout")
async def logout(
    current_user: CurrentUser, credentials: BearerDep, session: SessionDep, request: Request
):
    from app.auth.services import session_service as svc

    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        return {"ok": True}

    jti = payload.get("jti")
    ip = request.client.host if request.client else "unknown"

    if jti:
        # Revoke the DB session (create_session uses the same JTI for access + refresh tokens).
        await svc.revoke_session_by_jti(session, jti, current_user.id)

        # Also block the access token in Redis so it's rejected for its remaining lifetime.
        exp = payload.get("exp")
        if exp:
            ttl = max(0, int(exp - datetime.now(UTC).timestamp()))
        else:
            ttl = settings.access_token_expire_seconds
        await block_token(jti, ttl)

    await _audit(session, AuditEvent.LOGOUT, user_id=current_user.id, ip_address=ip)
    return {"ok": True}


@router.post(
    "/change-password",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def change_password(
    body: ChangePasswordRequest, current_user: CurrentUser, session: SessionDep, request: Request
):
    from app.auth.security.password_history import (
        add_password_to_history,
        check_password_not_reused,
    )

    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect"
        )

    if not await check_password_not_reused(session, current_user.id, body.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password was recently used"
        )

    new_hashed = hash_password(body.new_password)
    await add_password_to_history(session, current_user.id, current_user.hashed_password)
    current_user.hashed_password = new_hashed
    session.add(current_user)
    await session.commit()

    ip = request.client.host if request.client else "unknown"
    await _audit(session, AuditEvent.PASSWORD_CHANGED, user_id=current_user.id, ip_address=ip)
    return {"ok": True}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, session: SessionDep):
    import hashlib
    import logging
    import secrets
    from datetime import timedelta

    from app.auth.db_models import PasswordResetToken

    logger = logging.getLogger("fastauth.auth")
    user = await store.get_by_email(session, body.email)
    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(reset_token)
        await session.commit()
        logger.debug("Password reset token for user %s: %s", user.id, raw_token)

    return {"message": "If that email exists, a reset link was sent"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, session: SessionDep, request: Request):
    import hashlib

    from sqlmodel import select

    from app.auth.db_models import PasswordResetToken
    from app.auth.services import session_service as svc

    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    now = datetime.now(UTC)

    result = await session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),  # type: ignore
            PasswordResetToken.expires_at > now,
        )
    )
    reset_token = result.first()
    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )

    user = await store.get_by_id(session, reset_token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

    from app.auth.security.password_history import (
        add_password_to_history,
        check_password_not_reused,
    )

    if not await check_password_not_reused(session, user.id, body.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password was recently used"
        )

    await add_password_to_history(session, user.id, user.hashed_password)
    user.hashed_password = hash_password(body.new_password)
    reset_token.used_at = now
    session.add(user)
    session.add(reset_token)
    await session.commit()

    await svc.revoke_all_user_sessions(session, user.id)

    ip = request.client.host if request.client else "unknown"
    await _audit(session, AuditEvent.PASSWORD_RESET, user_id=user.id, ip_address=ip)
    return {"ok": True}


@router.post("/verify-email", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def verify_email(body: VerifyEmailRequest, session: SessionDep, request: Request):
    import hashlib

    from sqlmodel import select

    from app.auth.db_models import EmailVerificationToken

    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    now = datetime.now(UTC)

    result = await session.exec(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used_at.is_(None),  # type: ignore
            EmailVerificationToken.expires_at > now,
        )
    )
    vtoken = result.first()
    if vtoken is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = await store.get_by_id(session, vtoken.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

    vtoken.used_at = now
    user.email_verified = True
    session.add(vtoken)
    session.add(user)
    await session.commit()

    ip = request.client.host if request.client else "unknown"
    await _audit(session, AuditEvent.EMAIL_VERIFIED, user_id=user.id, ip_address=ip)
    return {"ok": True}


@router.post("/resend-verification", dependencies=[Depends(RateLimiter(times=3, seconds=60))])
async def resend_verification(body: ResendVerificationRequest, session: SessionDep):
    _neutral = {"message": "If that email exists and is unverified, a new link was sent"}

    user = await store.get_by_email(session, str(body.email))
    if user is None or user.email_verified:
        return _neutral

    await _issue_verification_token(session, user)
    await _audit(session, AuditEvent.EMAIL_VERIFICATION_SENT, user_id=user.id)
    return _neutral
