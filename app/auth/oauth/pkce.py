import base64
import hashlib
import secrets


def generate_code_verifier(length: int = 64) -> str:
    """Generate a cryptographically random code verifier (RFC 7636)."""
    return secrets.token_urlsafe(length)


def generate_code_challenge(verifier: str, method: str = "S256") -> str:
    """Derive code challenge from verifier. Only S256 is supported."""
    if method != "S256":
        raise ValueError("Only S256 code challenge method is supported")
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def verify_code_challenge(verifier: str, challenge: str, method: str = "S256") -> bool:
    """Return True if the verifier matches the stored challenge."""
    if method != "S256":
        return False
    return generate_code_challenge(verifier, method) == challenge
