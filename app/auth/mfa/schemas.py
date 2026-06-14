from pydantic import BaseModel, ConfigDict


class MfaSetupResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "secret": "BASE32SECRETEXAMPLEKEY234567",
        "qr_code_uri": "otpauth://totp/fastauth:alice?secret=BASE32SECRETEXAMPLEKEY234567&issuer=fastauth",
        "backup_codes": ["abc12345", "def67890", "ghi11223"],
    }})

    secret: str
    qr_code_uri: str
    backup_codes: list[str]


class MfaVerifyRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"code": "123456"}})

    code: str


class MfaBackupCodesResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"backup_codes": ["abc12345", "def67890", "ghi11223"]}})

    backup_codes: list[str]


class MfaLoginRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "mfa_session_token": "mfa-session-token-example",
        "code": "123456",
        "is_backup_code": False,
    }})

    mfa_session_token: str
    code: str
    is_backup_code: bool = False
