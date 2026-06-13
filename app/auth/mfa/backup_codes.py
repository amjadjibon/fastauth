import hashlib
import secrets


def generate_backup_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(count)]


def hash_backup_codes(codes: list[str]) -> list[str]:
    return [hashlib.sha256(c.encode()).hexdigest() for c in codes]


def verify_backup_code(plain_code: str, code_hashes: list[str]) -> str | None:
    """Return the matching hash if code is valid, else None."""
    code_hash = hashlib.sha256(plain_code.encode()).hexdigest()
    if code_hash in code_hashes:
        return code_hash
    return None
