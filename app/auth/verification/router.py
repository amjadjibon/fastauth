from fastapi import APIRouter, Depends, Request, status

from app.auth import store
from app.auth.audit.events import AuditEvent
from app.auth.audit.service import audit_log as _audit
from app.auth.deps import SessionDep
from app.auth.verification import service as verification_service
from app.auth.verification.schemas import ResendVerificationRequest, VerifyEmailRequest
from app.core.ratelimit import RateLimiter
from fastapi import HTTPException

router = APIRouter(prefix="/auth", tags=["auth"])


# Re-exported for use in auth/router.py register flow
issue_verification_token = verification_service.issue_verification_token


@router.post("/verify-email", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def verify_email(body: VerifyEmailRequest, session: SessionDep, request: Request):
    user, error = await verification_service.verify_email(session, body.token)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    ip = request.client.host if request.client else "unknown"
    await _audit(session, AuditEvent.EMAIL_VERIFIED, user_id=user.id, ip_address=ip)  # type: ignore[union-attr]
    return {"ok": True}


@router.post("/resend-verification", dependencies=[Depends(RateLimiter(times=3, seconds=60))])
async def resend_verification(body: ResendVerificationRequest, session: SessionDep):
    _neutral = {"message": "If that email exists and is unverified, a new link was sent"}

    user = await store.get_by_email(session, str(body.email))
    if user is None or user.email_verified:
        return _neutral

    await verification_service.issue_verification_token(session, user)
    await _audit(session, AuditEvent.EMAIL_VERIFICATION_SENT, user_id=user.id)
    return _neutral
