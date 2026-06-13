import pyotp


def generate_secret() -> str:
    return pyotp.random_base32()


def generate_qr_code_uri(secret: str, username: str, issuer: str = "FastAuth") -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=valid_window)
