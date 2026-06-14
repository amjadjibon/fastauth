import hashlib
import secrets

import pyotp


def generate_secret() -> str:
    return pyotp.random_base32()


def generate_qr_code_uri(secret: str, username: str, issuer: str = "FastAuth") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=valid_window)


def generate_backup_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(count)]


def hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def verify_backup_code(plain_code: str, code_hashes: list[str]) -> str | None:
    """Return the matching hash if code is valid, else None."""
    h = hash_backup_code(plain_code)
    return h if h in code_hashes else None
