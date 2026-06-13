# Security Best Practices

## Secrets Management

### SECRET_KEY

- Generate with `openssl rand -hex 32` — never use a guessable or short value
- Rotate annually or after any suspected compromise
- Store in a secrets manager (AWS Secrets Manager, HashiCorp Vault, Kubernetes Secrets) — never commit to version control
- If you rotate, old tokens will be invalidated; plan for a rolling restart window

### Database Credentials

- Use a dedicated service account with only the permissions FastAuth needs (no superuser)
- Enable SSL for the PostgreSQL connection: append `?ssl=require` to `DATABASE_URL`

### Social Provider Secrets

- Register one OAuth app per environment (dev/staging/prod) to limit blast radius
- Restrict allowed redirect URIs in each provider's console to exact production URLs

---

## Rate Limiting

FastAuth rate-limits on two axes:

| Axis | Default | Config env var |
|------|---------|---------------|
| Per IP (login) | 5 attempts / 5 min | `BRUTE_FORCE_MAX_ATTEMPTS`, `BRUTE_FORCE_WINDOW_SECONDS` |
| Per user (login) | 5 attempts → 15 min lockout | same |
| Registration | 10 requests / min | configured in `app/core/limiter.py` |

For production deployments behind a load balancer, ensure `X-Forwarded-For` is trusted only from your proxy IPs; otherwise clients can spoof IPs to bypass per-IP rate limits.

---

## Brute-Force Protection

The `BruteForceProtection` class in `app/auth/security/brute_force.py`:

- Tracks failed login attempts per key (IP or username) in Redis (or in-memory fallback)
- After `BRUTE_FORCE_MAX_ATTEMPTS` (default 5) failures in a window, the key is locked for `LOCKOUT_DURATION_SECONDS` (default 900 = 15 min)
- Returns `429 Too Many Requests` for locked keys
- Clears the counter on successful login

**Recommendation**: Use Redis in production for distributed brute-force protection across replicas. In-memory counters are per-process and won't share state.

---

## Session Security

- Refresh tokens use JTI (JWT ID) that is stored in `user_sessions`; every validation checks the DB
- Refresh token rotation: each refresh call invalidates the old JTI and issues a new one — replay attacks using a stolen refresh token fail after the first legitimate use
- `DELETE /auth/sessions` revokes all active sessions for a user (use after password change or suspected compromise)
- Sessions carry device info and IP; expose `GET /auth/sessions` in your UI so users can audit and revoke unfamiliar sessions

---

## Token Configuration

| Token | Default lifetime | Recommendation |
|-------|-----------------|----------------|
| Access token | 15 minutes | Keep short; extend only if unavoidable |
| Refresh token | 30 days | Align with your session inactivity policy |
| MFA session token | 5 minutes | Do not increase |

Set `ACCESS_TOKEN_EXPIRE_MINUTES` and `REFRESH_TOKEN_EXPIRE_DAYS` in your environment.

---

## HTTPS / Transport Security

- **Always** terminate TLS before the FastAuth process — never run plaintext HTTP in production
- Set `SECURE_COOKIES=true` to enforce `Secure` flag on any cookies
- The app emits `Strict-Transport-Security` headers when behind a trusted proxy — configure `TRUSTED_PROXY_IPS` accordingly
- Do not expose `/metrics` or `/docs` (OpenAPI) to the public internet — restrict with nginx `allow`/`deny` or a sidecar

---

## CORS

Set `ALLOWED_ORIGINS` to only the origins that legitimately call your API:

```
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```

Avoid `*` in production — it disables the Same-Origin Policy for your auth API.

---

## Audit Logging

All security-relevant events are written to `audit_logs` with PII masking:

- Email addresses are masked: `j***@example.com`
- IP addresses are masked: last octet zeroed (`192.168.1.0`)

Review audit logs regularly for:

- Spike in `login_failed` events (brute-force indicator)
- `mfa_disabled` events (potential account takeover)
- Admin actions on sensitive accounts

Export logs for SIEM integration via `GET /auth/audit/logs/export?format=json`.

---

## MFA Recommendations

- Enforce MFA for admin accounts: set `MFA_REQUIRED_FOR_ALL_USERS=true` or apply per-role enforcement
- Backup codes are one-time-use SHA-256 hashes in the DB — treat them like passwords
- Prompt users to regenerate backup codes after any account recovery event

---

## Dependency Scanning

Run regularly:
```bash
uv run pip-audit           # check for known CVEs in dependencies
uv run bandit -r app/      # static security analysis
```

---

## Incident Response

1. **Suspected token leak**: `DELETE /auth/sessions` for the affected user + rotate `SECRET_KEY`
2. **Brute-force in progress**: Temporarily lower `BRUTE_FORCE_MAX_ATTEMPTS` to 3; block offending CIDR at the network edge
3. **Compromised admin account**: Use DB-level update `UPDATE users SET is_active=false WHERE id=<id>` as a break-glass if the API is inaccessible
4. **Credential stuffing**: Enable MFA enforcement, increase lockout duration, add CAPTCHA to the login endpoint
