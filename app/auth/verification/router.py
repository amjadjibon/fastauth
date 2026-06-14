import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select, update

from app.auth import store
from app.auth.audit.events import AuditEvent
from app.auth.audit.logger import audit_log as _audit
from app.auth.db_models import EmailVerificationToken
from app.auth.deps import SessionDep
from app.auth.schemas import ResendVerificationRequest, VerifyEmailRequest
from app.core.email import send_verification_email
from app.core.ratelimit import RateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])


async def issue_verification_token(session, user, *, commit: bool = True) -> str:
    """Stage a new verification token, invalidating existing unused ones first.

    When commit=False the caller is responsible for the commit (used in register
    to atomically create both the user row and the token row).
    """
    await session.exec(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),  # type: ignore
        )
        .values(used_at=datetime.now(UTC))
    )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    session.add(EmailVerificationToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))

    if commit:
        await session.commit()
        await send_verification_email(user.id, user.email, raw_token)

    return raw_token


@router.post("/verify-email", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def verify_email(body: VerifyEmailRequest, session: SessionDep, request: Request):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    now = datetime.now(UTC)

    result = await session.exec(
        select(EmailVerificationToken)
        .where(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used_at.is_(None),  # type: ignore
            EmailVerificationToken.expires_at > now,
        )
        .with_for_update()
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

    await issue_verification_token(session, user)
    await _audit(session, AuditEvent.EMAIL_VERIFICATION_SENT, user_id=user.id)
    return _neutral
