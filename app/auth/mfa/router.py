from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import CurrentUser, SessionDep
from app.auth.mfa.models import MfaBackupCodesResponse, MfaSetupResponse, MfaVerifyRequest
from app.auth.mfa.totp import generate_qr_code_uri, generate_secret, verify_totp
from app.auth.services import mfa_service

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


@router.post("/setup", response_model=MfaSetupResponse)
async def setup_mfa(current_user: CurrentUser, session: SessionDep):
    secret = generate_secret()
    qr_uri = generate_qr_code_uri(secret, username=current_user.username)
    backup_codes = await mfa_service.generate_backup_codes(session, current_user.id)
    await mfa_service.enable_mfa(session, current_user.id, encrypted_secret=secret)
    return MfaSetupResponse(secret=secret, qr_code_uri=qr_uri, backup_codes=backup_codes)


@router.post("/verify")
async def verify_mfa(body: MfaVerifyRequest, current_user: CurrentUser, session: SessionDep):
    mfa = await mfa_service.get_mfa_secret(session, current_user.id)
    if mfa is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not set up")

    if not verify_totp(mfa.secret_encrypted, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")

    await mfa_service.verify_totp(session, current_user.id, body.code)
    return {"message": "MFA verified and enabled"}


@router.delete("/disable")
async def disable_mfa(body: MfaVerifyRequest, current_user: CurrentUser, session: SessionDep):
    mfa = await mfa_service.get_mfa_secret(session, current_user.id)
    if mfa is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not set up")
    if not verify_totp(mfa.secret_encrypted, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")
    await session.delete(mfa)
    await session.commit()
    return {"message": "MFA disabled"}


@router.post("/backup-codes", response_model=MfaBackupCodesResponse)
async def regenerate_backup_codes(
    body: MfaVerifyRequest, current_user: CurrentUser, session: SessionDep
):
    mfa = await mfa_service.get_mfa_secret(session, current_user.id)
    if mfa is None or not mfa.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA not active")
    if not verify_totp(mfa.secret_encrypted, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")
    codes = await mfa_service.generate_backup_codes(session, current_user.id)
    return MfaBackupCodesResponse(backup_codes=codes)
