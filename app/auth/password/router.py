from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import store
from app.auth.audit.events import AuditEvent
from app.auth.audit.service import audit_log as _audit
from app.auth.deps import CurrentUser, SessionDep
from app.auth.password import service as password_service
from app.auth.password.schemas import ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
from app.auth.sessions import service as session_service
from app.core.ratelimit import RateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/change-password", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def change_password(
    body: ChangePasswordRequest, current_user: CurrentUser, session: SessionDep, request: Request
):
    ok, error = await password_service.change_password(
        session, current_user, body.current_password, body.new_password
    )
    if not ok:
        status_code = status.HTTP_401_UNAUTHORIZED if error == "Current password is incorrect" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=error)

    ip = request.client.host if request.client else "unknown"
    await _audit(session, AuditEvent.PASSWORD_CHANGED, user_id=current_user.id, ip_address=ip)
    return {"ok": True}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, session: SessionDep):
    user = await store.get_by_email(session, body.email)
    if user:
        await password_service.issue_reset_token(session, user)
    return {"message": "If that email exists, a reset link was sent"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, session: SessionDep, request: Request):
    user, error = await password_service.reset_password(session, body.token, body.new_password)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    await session_service.revoke_all_user_sessions(session, user.id)  # type: ignore[union-attr]

    ip = request.client.host if request.client else "unknown"
    await _audit(session, AuditEvent.PASSWORD_RESET, user_id=user.id, ip_address=ip)  # type: ignore[union-attr]
    return {"ok": True}
