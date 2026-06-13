"""JWKS endpoint handler.

Returns empty keyset for HS256 (symmetric — no public key to expose).
Returns a proper RSA JWK when ALGORITHM=RS256 and RSA_PRIVATE_KEY_PATH is set.
"""

from app.core.config import settings


def get_jwks() -> dict:
    if settings.algorithm != "RS256" or not settings.rsa_private_key_path:
        return {"keys": []}

    try:
        import base64

        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        with open(settings.rsa_private_key_path, "rb") as f:
            private_key = load_pem_private_key(f.read(), password=None)

        numbers = private_key.public_key().public_numbers()  # type: ignore

        def _b64(n: int) -> str:
            byte_length = (n.bit_length() + 7) // 8
            return base64.urlsafe_b64encode(n.to_bytes(byte_length, "big")).rstrip(b"=").decode()

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": "default",
                    "n": _b64(numbers.n),  # type: ignore
                    "e": _b64(numbers.e),  # type: ignore
                }
            ]
        }
    except Exception:
        return {"keys": []}
