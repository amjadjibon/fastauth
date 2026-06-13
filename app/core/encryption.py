"""Fernet AES-256 encrypt/decrypt helpers keyed from settings.secret_key.

Key derivation: SHA-256(secret_key) → base64url → valid Fernet key (32 bytes).

Re-encryption note: If SECRET_KEY is rotated, all existing encrypted values
(MFA secrets, social tokens) become unreadable. Before rotating:
  1. Read each row, decrypt with old key, re-encrypt with new key.
  2. Update the rows in a single transaction.
  3. Then rotate SECRET_KEY in the environment.
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
