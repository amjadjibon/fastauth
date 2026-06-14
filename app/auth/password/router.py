import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.auth import store
from app.auth.audit.events import AuditEvent
from app.auth.audit.logger import audit_log as _audit
from app.auth.models import PasswordResetToken
from app.auth.deps import CurrentUser, SessionDep
from app.auth.schemas import ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
from app.auth.security.password_history import add_password_to_history, check_password_not_reused
from app.core.ratelimit import RateLimiter
from app.core.security import hash_password, verify_password

logger = logging.getLogger("fastauth.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/change-password", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def change_password(
    body: ChangePasswordRequest, current_user: CurrentUser, session: SessionDep, request: Request
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect"
        )

    if not await check_password_not_reused(session, current_user.id, body.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password was recently used"
        )

    await add_password_to_history(session, current_user.id, current_user.hashed_password)
    current_user.hashed_password = hash_password(body.new_password)
    session.add(current_user)
    await session.commit()

    ip = request.client.host if request.client else "unknown"
    await _audit(session, AuditEvent.PASSWORD_CHANGED, user_id=current_user.id, ip_address=ip)
    return {"ok": True}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, session: SessionDep):
    user = await store.get_by_email(session, body.email)
    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        session.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        await session.commit()
        logger.debug("Password reset token issued for user %s", user.id)

    return {"message": "If that email exists, a reset link was sent"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, session: SessionDep, request: Request):
    from app.auth.services import session_service as svc

    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    now = datetime.now(UTC)

    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),  # type: ignore
            PasswordResetToken.expires_at > now,
        )
    )
    reset_token = result.scalar_one_or_none()
    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )

    user = await store.get_by_id(session, reset_token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

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
