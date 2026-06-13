from pydantic import BaseModel


class MfaSetupResponse(BaseModel):
    secret: str
    qr_code_uri: str
    backup_codes: list[str]


class MfaVerifyRequest(BaseModel):
    code: str


class MfaBackupCodesResponse(BaseModel):
    backup_codes: list[str]


class MfaLoginRequest(BaseModel):
    mfa_session_token: str
    code: str
    is_backup_code: bool = False
