---
iteration: 1
verdict: Request Changes
---

# Code Review — Email Verification (Iteration 1)

## Verdict: Request Changes

## Summary

The core cryptographic design is sound — `secrets.token_urlsafe(32)` gives 256 bits of entropy and SHA-256 hashing is appropriate — but three High-severity issues must be addressed before this can merge: the raw verification token is logged at DEBUG level and the `fastauth` logger is configured at DEBUG in `conf/log.yaml`, meaning every deployed environment leaks tokens to stdout; the social login callback (`/auth/social/{provider}/callback`) creates sessions without checking `email_verified`, bypassing the gate entirely; and `_issue_verification_token` commits the user record and the token in two separate database transactions so a failure mid-registration leaves the user permanently stuck with no token to verify with. Several Medium issues (TOCTOU race on token consumption, no old-token invalidation on resend, missing per-email rate limiting) and a handful of Low/Info items round out the findings.

---

## Findings

### Critical

None.

---

### High

**HIGH-001: Raw verification token written to production logs**

`app/core/email.py` line 8:
```python
logger.debug("Email verification token for user %s (%s): %s", user_id, email, token)
```

`conf/log.yaml` sets `fastauth` logger to `level: DEBUG`, meaning this fires in every environment including production. A raw token in structured JSON logs (streamed to stdout or a log aggregator) becomes a credential — anyone with log read access can verify any email address or account-takeover if verification grants implicit login. The password-reset stub in `router.py` line 324 has the identical problem.

**Fix:** Remove the token from this log line entirely. Log a non-sensitive confirmation such as `"Verification email queued for user %s", user_id`. Separately, raise the `fastauth` logger level to `INFO` in the production log config, or use a separate config profile.

---

**HIGH-002: Social login callback bypasses the email verification gate**

`app/auth/social/router.py` lines 117–143 call `create_session()` directly after a successful OAuth exchange. `require_email_verification` is never consulted, and `email_verified` is never set for socially-created users (`auto_create_user_on_social_login` in `social_service.py` lines 81–100 creates the `User` with `email_verified=False` by default).

An operator who sets `REQUIRE_EMAIL_VERIFICATION=true` to enforce verification for password-based accounts leaves the entire social login surface completely ungated. Additionally, socially-created users whose addresses are provider-verified (Google, GitHub) are treated the same as unverified addresses, which is the wrong default.

**Fix (two-part):**
1. In `social_service.auto_create_user_on_social_login`, accept a boolean `email_verified` argument and set it on the `User` row when the provider vouches for the address (providers that return a verified email field).
2. In `social_callback` (and the OAuth2 `/token` endpoint if it issues sessions directly), check `settings.require_email_verification and not user.email_verified` before calling `create_session`, mirroring the guard in the password-login flow.

---

**HIGH-003: Split transactions leave users in an unrecoverable limbo on registration failure**

`store.create_user` (line 11) does `await session.commit()` before returning. `_issue_verification_token` then does a *second* `await session.commit()` on line 55. If the second commit fails (DB error, connection loss) the user row exists but has no verification token, and the register endpoint returns HTTP 500. The client, seeing a 500, may retry; the retry hits the DB unique constraint on `email` and gets an unhandled `IntegrityError` (also a 500), not the expected 409. The original user record is now permanently stuck: no token, no way to trigger one except via `/auth/resend-verification` (which requires knowing the flow failed silently).

Separately, if `send_verification_email` raises after both commits succeed (network error), token + user exist in the DB but the caller still gets a 500, and the client may retry, getting an `IntegrityError` on the second user-creation attempt.

**Fix:** Wrap user creation and token creation in a single unit of work. Move `session.add(user); session.add(token)` into a single `await session.commit()` call, so either both are durable or neither is. `send_verification_email` should be called outside the transaction; if it fails, return 201 (the user is created and the token is in the DB — `/resend-verification` exists for exactly this case). Catch `IntegrityError` on `email` uniqueness separately from `username` and return a 409 with a distinct message.

---

### Medium

**MED-001: TOCTOU race condition on token consumption in `verify_email`**

`verify_email` (lines 393–412) runs a `SELECT … WHERE used_at IS NULL` and then separately sets `vtoken.used_at = now` in a subsequent `UPDATE`. Under concurrent requests (browser double-submit, replayed request) two requests can both pass the SELECT before either UPDATE commits, resulting in double-verification writes. While `email_verified = True` twice is idempotent here, the pattern is a footgun for any future logic added to this handler.

**Fix:** Use `SELECT … FOR UPDATE` (SQLAlchemy `with_for_update()`) on the token row, or use a single `UPDATE email_verification_tokens SET used_at = now WHERE token_hash = :hash AND used_at IS NULL RETURNING id` and check rows-affected == 1. The same pattern should be applied to `reset_password`.

---

**MED-002: `_issue_verification_token` does not invalidate previous tokens on resend**

Each call to `resend_verification` appends a new row to `email_verification_tokens` without invalidating existing valid tokens for the same user. A user who requests many resends accumulates multiple live tokens — all usable until they expire 24 hours later. This widens the attack window for token theft and creates unnecessary DB growth.

**Fix:** Add `DELETE FROM email_verification_tokens WHERE user_id = :uid AND used_at IS NULL` (or a bulk `UPDATE … SET used_at = now`) inside `_issue_verification_token` before inserting the new row, within the same transaction.

---

**MED-003: No per-email (or per-user) rate limit on `resend-verification` and `forgot-password`**

Both endpoints are rate-limited at 3 req/60 s *per source IP*. An attacker who controls multiple IPs (bot farm, residential proxies) can direct arbitrary volumes of email at a single victim address, enabling email-bombing. The `resend-verification` neutral response correctly prevents enumeration, but does not prevent mail-flooding.

**Fix:** Add a per-email (or per-`user_id`) rate limit in addition to the IP-based one — for example, `rl:resend:{sha256(email_lower)}` with a 2-per-hour window — using the same `is_rate_limited` helper. Apply the same treatment to `forgot-password`.

---

**MED-004: `token_hash` column in `email_verification_tokens` lacks a UNIQUE constraint**

The `EmailVerificationToken` model (db_models.py line 350) declares `token_hash` with `index=True` but not `unique=True`. The migration (lines 35–35) creates only a plain index. By contrast, `PasswordResetToken.token_hash` is also not unique in the model (line 328), but `OAuthRefreshToken.token_hash` *is* unique (line 97). A SHA-256 collision is astronomically unlikely, but:

1. There is no DB-level guard against a software bug accidentally inserting duplicate hashes.
2. The missing constraint is inconsistent with the other sensitive-token tables.

**Fix:** Add `unique=True` to `token_hash` in `EmailVerificationToken` (and `PasswordResetToken`) and add `op.create_unique_constraint` to the migration (or regenerate it).

---

### Low

**LOW-001: Imports inside function bodies (`_issue_verification_token` and login)**

`_issue_verification_token` (lines 44–46) imports `hashlib`, `secrets`, `timedelta`, and `EmailVerificationToken` on every invocation. The `login` handler (lines 99–103) does the same for `session_service`, `parse_user_agent`, and `_redis`. Deferred imports are occasionally useful to break circular dependencies, but these have none and pay a small (but repeated) import-machinery tax on every hot-path request.

**Fix:** Move all these imports to the module top-level.

---

**LOW-002: `VerifyEmailRequest.token` has no maximum length**

`token: str = Field(min_length=1)` (models.py line 96) accepts arbitrarily long strings. A `secrets.token_urlsafe(32)` token is 43 characters; there is no reason to hash a 1 MB payload. Add `max_length=128` (or at minimum 256) to prevent hash-computation DoS from oversized inputs.

---

**LOW-003: Brute-force counter is cleared before the email-verification check**

In `login` (lines 133–137), `_redis.delete(f"bf:attempts:user:{username}", ...)` executes on line 134, clearing the failed-login counter, before the `require_email_verification` check on line 136 which may return 403. An attacker who knows a valid username+password but whose account is unverified can use repeated login attempts to reset their brute-force window indefinitely without ever gaining a session.

This is low-severity because: (a) the attacker must already have the correct credentials, (b) the 403 "Email not verified" leaks no new information about other accounts, and (c) the brute-force counter is keyed on username, not email. Still, the counter should only be cleared on a fully successful authentication.

**Fix:** Move the `_redis.delete(...)` call to after the email-verification check passes (i.e., just before the audit log on line 140).

---

**LOW-004: `require_email_verification` not enforced in the OAuth2 password-grant flow**

If the project's OAuth2 router (`app/auth/oauth/router.py`) includes a Resource Owner Password Credentials grant, that path does not reference `settings.require_email_verification`. Confirm whether a ROPC grant exists and, if so, add the same guard applied in the social login fix (HIGH-002).

*(Inspection showed the OAuth2 router has no direct reference — confirm there is no ROPC endpoint before closing this item.)*

---

**LOW-005: Test uses global `settings` mutation without asyncio isolation**

`test_login_blocked_when_unverified` and `test_login_allowed_after_verification` mutate `settings.require_email_verification` directly using a try/finally guard (lines 102–111, 121–134). This is not thread-safe if pytest-asyncio ever runs tests concurrently, and it leaves the shared settings object in a mutated state if an exception escapes the try block before the finally. Prefer `unittest.mock.patch.object(settings, "require_email_verification", True)` as a context manager, which is both exception-safe and explicit.

---

### Info

**INFO-001: `send_verification_email` is a stub — integration test gap**

`app/core/email.py` is explicitly a stub with a comment "Replace with real SMTP when ready." No test verifies that the function signature, argument order, or call contract matches what a real SMTP integration would expect. Consider adding a narrow integration test (or at minimum an interface contract test) now, before the stub is replaced, so the replacement doesn't silently break the call site.

---

**INFO-002: No expiry index on `email_verification_tokens`**

The `expires_at` column has no index. As the table grows, the `SELECT … WHERE expires_at > now` in `verify_email` will perform a full-table scan on larger deployments. Add a composite index on `(token_hash, expires_at, used_at)` or at minimum a separate index on `expires_at` to support future cleanup queries and the WHERE clause in `verify_email`.

---

**INFO-003: No scheduled job to prune expired tokens**

There is no background task or cron job to delete expired / consumed rows from `email_verification_tokens` (or `password_reset_tokens`). Both tables will grow unboundedly. This is a future operational concern rather than a blocking issue, but a migration or a startup hook that purges `WHERE expires_at < now - interval '7 days'` should be planned.

---

**INFO-004: `RegisterResponse` does not indicate verification-pending state**

`POST /auth/register` returns `{"user_id": "..."}` with no indication that a verification email was sent. API clients (mobile apps, SPAs) have no machine-readable way to distinguish a "verify your email" flow from a "you can log in now" flow. Consider adding `email_verification_required: bool` to `RegisterResponse` so clients can display the appropriate UI without hard-coding the server-side flag.
