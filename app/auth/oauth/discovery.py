from app.auth.oauth.models import OIDCDiscoveryResponse
from app.core.config import settings


def get_oidc_discovery(base_url: str) -> OIDCDiscoveryResponse:
    return OIDCDiscoveryResponse(
        issuer=base_url,
        authorization_endpoint=f"{base_url}/oauth/authorize",
        token_endpoint=f"{base_url}/oauth/token",
        userinfo_endpoint=f"{base_url}/oauth/userinfo",
        jwks_uri=f"{base_url}/.well-known/jwks.json",
        scopes_supported=["openid", "profile", "email", "offline_access"],
        response_types_supported=["code"],
        grant_types_supported=["authorization_code", "refresh_token"],
        subject_types_supported=["public"],
        id_token_signing_alg_values_supported=[settings.algorithm],
        token_endpoint_auth_methods_supported=["client_secret_basic", "none"],
    )
