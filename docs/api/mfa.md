# Multi-Factor Authentication (MFA) API Reference

FastAuth supports TOTP-based MFA (RFC 6238) using apps like Google Authenticator, Authy, or 1Password.

## Setup Flow

### 1. Initiate MFA Setup: `POST /auth/mfa/setup`

Requires `Authorization: Bearer <access_token>`.

**Response** `200 OK`
```json
{
  "secret": "BASE32ENCODEDSECRET",
  "qr_code_uri": "otpauth://totp/FastAuth:johndoe?secret=BASE32...&issuer=FastAuth",
  "backup_codes": [
    "A1B2C3D4", "E5F6G7H8", "..."
  ]
}
```

Display the `qr_code_uri` as a QR code for the user to scan. Store `backup_codes` securely — they are shown only once.

### 2. Verify and Activate: `POST /auth/mfa/verify`

Requires `Authorization: Bearer <access_token>`.

**Request body**
```json
{
  "code": "123456"
}
```

**Response** `200 OK` — MFA is now active for the account.

### Disable MFA: `DELETE /auth/mfa/disable`

Requires `Authorization: Bearer <access_token>`.

**Request body**
```json
{
  "code": "123456"
}
```

### Regenerate Backup Codes: `POST /auth/mfa/backup-codes`

Requires `Authorization: Bearer <access_token>` and current TOTP code.

**Response** `200 OK`
```json
{
  "backup_codes": ["NEW1CODE", "NEW2CODE", "..."]
}
```

Old backup codes are invalidated.

---

## MFA Login Flow

When a user has MFA enabled, the standard login response includes:

```json
{
  "mfa_required": true,
  "mfa_session_token": "short-lived-token",
  "access_token": null
}
```

### Complete Login: `POST /auth/login/mfa`

**Request body**
```json
{
  "mfa_session_token": "short-lived-token",
  "code": "123456"
}
```

`code` may be either a 6-digit TOTP code or an 8-character backup code (e.g. `A1B2C3D4`).

**Response** `200 OK`
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "Bearer"
}
```

---

## Notes

- TOTP codes are valid for ±30 seconds (1 step drift tolerance)
- Each backup code can only be used once
- MFA secrets are stored encrypted in the database
- The `mfa_session_token` expires after 5 minutes
