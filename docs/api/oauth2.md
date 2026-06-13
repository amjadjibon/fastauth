# OAuth2 / OIDC API Reference

FastAuth implements OAuth2 Authorization Code Flow with PKCE (RFC 7636) and OpenID Connect (OIDC) Discovery.

## Discovery Endpoints

### GET `/.well-known/openid-configuration`

Returns the OIDC provider metadata document.

**Response** `200 OK`
```json
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/oauth/authorize",
  "token_endpoint": "https://auth.example.com/oauth/token",
  "userinfo_endpoint": "https://auth.example.com/oauth/userinfo",
  "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
  "scopes_supported": ["openid", "profile", "email"],
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "token_endpoint_auth_methods_supported": ["client_secret_basic", "none"],
  "code_challenge_methods_supported": ["S256"]
}
```

### GET `/.well-known/jwks.json`

Returns the JSON Web Key Set (JWKS) for token verification.

---

## Authorization Code Flow with PKCE

### Step 1 — Generate PKCE values (client side)

```python
import secrets, hashlib, base64

code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
digest = hashlib.sha256(code_verifier.encode()).digest()
code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
```

### Step 2 — Authorize: `POST /oauth/authorize`

Requires Bearer token (authenticated user consenting).

**Request body**
```json
{
  "response_type": "code",
  "client_id": "my-app",
  "redirect_uri": "https://myapp.example.com/callback",
  "scope": "openid profile email",
  "state": "random-csrf-token",
  "code_challenge": "<S256-challenge>",
  "code_challenge_method": "S256"
}
```

**Response** `200 OK`
```json
{
  "code": "abc123def456...",
  "state": "random-csrf-token"
}
```

### Step 3 — Exchange code: `POST /oauth/token`

**Request body**
```json
{
  "grant_type": "authorization_code",
  "code": "abc123def456...",
  "redirect_uri": "https://myapp.example.com/callback",
  "client_id": "my-app",
  "code_verifier": "<original-verifier>"
}
```

**Response** `200 OK`
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_token": "eyJhbGci...",
  "scope": "openid profile email",
  "id_token": "eyJhbGci..."
}
```

**Error responses**: `400` for missing/invalid fields, `401` for PKCE mismatch.

### Refresh Token: `POST /oauth/token`

```json
{
  "grant_type": "refresh_token",
  "refresh_token": "eyJhbGci...",
  "client_id": "my-app"
}
```

Refresh tokens are rotated on every use — the old token is invalidated immediately.

### UserInfo: `GET /oauth/userinfo`

Requires `Authorization: Bearer <access_token>`.

**Response** `200 OK`
```json
{
  "sub": "user-uuid",
  "username": "johndoe",
  "email": "john@example.com",
  "email_verified": true
}
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| `invalid_request` | Missing required parameter |
| `invalid_client` | Client authentication failed |
| `invalid_grant` | Authorization code invalid or expired |
| `unsupported_grant_type` | Grant type not supported |
| `invalid_scope` | Requested scope unavailable |
