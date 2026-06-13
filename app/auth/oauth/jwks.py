"""JWKS endpoint handler.

For HS256 (symmetric), there are no public keys to expose. This module
returns an empty keyset. When the system is upgraded to RS256/ES256,
add the public key in JWK format here.
"""


def get_jwks() -> dict:
    return {"keys": []}
