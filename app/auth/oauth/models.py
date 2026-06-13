from pydantic import BaseModel


class AuthorizationCodeRequest(BaseModel):
    response_type: str = "code"
    client_id: str
    redirect_uri: str
    scope: str = "openid"
    state: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None
    nonce: str | None = None


class TokenRequest(BaseModel):
    grant_type: str
    code: str | None = None
    redirect_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    code_verifier: str | None = None
    refresh_token: str | None = None


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None


class OIDCDiscoveryResponse(BaseModel):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    scopes_supported: list[str]
    response_types_supported: list[str]
    grant_types_supported: list[str]
    subject_types_supported: list[str]
    id_token_signing_alg_values_supported: list[str]
    token_endpoint_auth_methods_supported: list[str]
