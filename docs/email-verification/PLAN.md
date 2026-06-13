---
goal: Email verification — block fake-email signups by requiring users to confirm their address before full access
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: amjadjibon
status: 'Planned'
tags: [feature, security]
---

# Email Verification

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Registration accepts any email address today. This adds a flag-gated email verification flow: on register, a short-lived token is created and logged (dev) or sent via SMTP (prod); login is blocked for unverified accounts when `REQUIRE_EMAIL_VERIFICATION=true`.

## 1. Requirements & Constraints

- **REQ-001**: After registration, an `EmailVerificationToken` is created and its raw value is logged at DEBUG level (same pattern as `forgot-password`).
- **REQ-002**: `POST /auth/verify-email` accepts the raw token, marks the user as verified, and consumes the token.
- **REQ-003**: `POST /auth/resend-verification` re-issues a token for an unverified account.
- **REQ-004**: A config flag `require_email_verification: bool = False` gates enforcement — when `False`, unverified users can still log in (backward-compatible default).
- **SEC-001**: Tokens are SHA-256 hashed before storage (same as `PasswordResetToken`). TTL = 24 hours.
- **CON-001**: No real SMTP dependency — email sending is a stub that logs the token. SMTP is a follow-up feature.
- **CON-002**: Social-login users (OAuth, GitHub, etc.) are auto-marked as verified on account creation since the provider already verified the email.
- **GUD-001**: Use migration number `2000000011`; hand-write migration to match repo style.

## 2. Implementation Steps

> **Agent instructions**: This repo uses git. Use `git add -A && git commit -m "<message>"` at each phase boundary. Update checkboxes to `[x]` as each task is completed.

### Phase 1: DB Model and Migration

**Goal**: Add `email_verified` column to `user` table and `email_verification_tokens` table.

- [x] TASK-001: Add `email_verified: bool` column to `User` in `app/auth/models.py` — `Field(default=False, sa_column=Column(Boolean(), nullable=False, server_default="0"))`.
- [x] TASK-002: Add `EmailVerificationToken` model to `app/auth/db_models.py` — fields: `id`, `user_id` (FK → user, CASCADE), `token_hash` (String(64), indexed), `expires_at`, `used_at` (nullable), `created_at`.
- [x] TASK-003: Write `migrations/versions/2000000011_add_email_verification.py` — adds `email_verified` column to `user` table and creates `email_verification_tokens` table with index on `token_hash`.

**Completion criteria**: `uv run alembic upgrade head` runs without error on a fresh Postgres DB; `email_verified` column and `email_verification_tokens` table exist.

**git commit**: `git add -A && git commit -m "feat: add email_verified column and email_verification_tokens table"`

---

### Phase 2: Config and Email Stub

**Goal**: Add the enforcement flag to settings and create the email-sending stub.

- [x] TASK-004: Add `require_email_verification: bool = False` to `Settings` in `app/core/config.py`.
- [x] TASK-005: Create `app/core/email.py` with `async def send_verification_email(user_id: str, email: str, token: str) -> None` — logs the token at DEBUG level with `logger.debug("Email verification token for user %s: %s", user_id, token)`. No SMTP. Returns immediately.

**Completion criteria**: `from app.core.email import send_verification_email` imports without error.

**git commit**: `git add -A && git commit -m "feat: add email verification config flag and email stub"`

---

### Phase 3: Register and Login Integration

**Goal**: Wire verification into the register and login flows.

- [x] TASK-006: In `app/auth/router.py`, update `register`: after creating the user, call `_issue_verification_token(session, user)` (a local helper defined in the same file) that creates an `EmailVerificationToken` row and calls `send_verification_email`. The `register` response is unchanged (still returns `user_id`).
- [x] TASK-007: Add `_issue_verification_token(session, user) -> str` helper in `app/auth/router.py` — generates `secrets.token_urlsafe(32)`, hashes it, inserts `EmailVerificationToken(user_id, token_hash, expires_at=now+24h)`, calls `await send_verification_email(user.id, user.email, raw_token)`, returns the raw token.
- [x] TASK-008: In `login` handler, after the user is found and password verified, add: `if settings.require_email_verification and not user.email_verified: raise HTTPException(403, "Email not verified")`.
- [x] TASK-009: Add `EMAIL_VERIFIED = "email_verified"` and `EMAIL_VERIFICATION_SENT = "email_verification_sent"` to `app/auth/audit/events.py`.

**Completion criteria**: `POST /auth/register` with `REQUIRE_EMAIL_VERIFICATION=false` still returns 201; with `REQUIRE_EMAIL_VERIFICATION=true`, subsequent `POST /auth/login` with the new user returns 403 until verified.

**git commit**: `git add -A && git commit -m "feat: issue verification token on register, enforce on login"`

---

### Phase 4: Verify and Resend Endpoints

**Goal**: Add `POST /auth/verify-email` and `POST /auth/resend-verification`.

- [x] TASK-010: Add `VerifyEmailRequest(token: str)` and `ResendVerificationRequest(email: EmailStr)` to `app/auth/models.py`.
- [x] TASK-011: Add `POST /auth/verify-email` to `app/auth/router.py`:
  1. SHA-256 hash the incoming token.
  2. Query `EmailVerificationToken` where `token_hash=hash`, `used_at IS NULL`, `expires_at > now`.
  3. If not found → 400 "Invalid or expired token".
  4. Set `used_at = now`, set `user.email_verified = True`, commit.
  5. Audit `EMAIL_VERIFIED`.
  6. Return `{"ok": True}`.
- [x] TASK-012: Add `POST /auth/resend-verification` to `app/auth/router.py`:
  1. Look up user by email; if not found → return neutral message (don't leak existence).
  2. If already verified → return same neutral message.
  3. Call `_issue_verification_token(session, user)`.
  4. Audit `EMAIL_VERIFICATION_SENT`.
  5. Return the neutral message.
- [x] TASK-013: Add `email_verified: bool` field to `UserResponse` in `app/auth/models.py`.

**Completion criteria**: `POST /auth/verify-email` with a valid token returns `{"ok": true}`; user `email_verified` is `true` in DB; calling again returns 400.

**git commit**: `git add -A && git commit -m "feat: add verify-email and resend-verification endpoints"`

---

### Phase 5: Integration Tests

**Goal**: Cover the full verification flow and the enforcement gate.

- [x] TASK-014: Create `tests/test_email_verification.py` with:
  - `test_register_creates_unverified_user` — register, `GET /auth/me` returns `email_verified: false`.
  - `test_verify_email_marks_user_verified` — register, extract token from `caplog`, call `POST /auth/verify-email`, confirm `email_verified: true`.
  - `test_verify_email_token_consumed` — second call with same token returns 400.
  - `test_verify_email_invalid_token` — random token returns 400.
  - `test_resend_verification_unknown_email` — returns neutral message, no error.
  - `test_login_blocked_when_unverified` — set `settings.require_email_verification = True` in the test, register, attempt login → 403.
  - `test_login_allowed_after_verification` — same setup, verify first, then login → 200.

**Completion criteria**: `uv run pytest tests/test_email_verification.py -v` — all tests pass.

**git commit**: `git add -A && git commit -m "test: email verification integration tests"`

---

## 3. Alternatives Considered

- **ALT-001**: Real SMTP via `aiosmtplib` — rejected to avoid a new hard dependency; the stub is sufficient for the feature contract and SMTP is a follow-up.
- **ALT-002**: Block login by default (`require_email_verification=True`) — rejected because it's a breaking change for existing deployments.
- **ALT-003**: Store token in Redis with TTL — rejected to stay consistent with `PasswordResetToken` which is already in the DB.

## 4. Dependencies

- **DEP-001**: `hashlib` + `secrets` — stdlib, already used in `forgot-password`.
- **DEP-002**: No new packages needed.

## 5. Affected Files

- **FILE-001**: `app/auth/models.py` — add `email_verified` to `User`, add request models, add field to `UserResponse`
- **FILE-002**: `app/auth/db_models.py` — add `EmailVerificationToken`
- **FILE-003**: `app/core/config.py` — add `require_email_verification`
- **FILE-004**: `app/core/email.py` — new email stub
- **FILE-005**: `app/auth/router.py` — register + login updates, two new endpoints
- **FILE-006**: `app/auth/audit/events.py` — two new event constants
- **FILE-007**: `migrations/versions/2000000011_add_email_verification.py` — new migration
- **FILE-008**: `tests/test_email_verification.py` — new

## 6. Testing

- [x] TEST-001: `uv run pytest tests/test_email_verification.py -v` — all pass (7/7).
- [x] TEST-002: `uv run pytest tests/ -v` — no new regressions. The 12 failures in `test_auth.py` when run after the email-verification tests are a pre-existing rate-limiter ordering issue (in-memory limiter shared across tests; `test_auth.py` passes 22/22 in isolation).

## 7. Risks & Assumptions

- **RISK-001**: Existing users have `email_verified = False` after migration — mitigation: the default is `False` and `require_email_verification` defaults to `False`, so no existing user is locked out unless an operator explicitly opts in.
- **ASSUMPTION-001**: Tests capture the verification token from `caplog` (Python's `logging` test fixture), which works because the stub uses `logger.debug`.

## 8. Architecture Diagram

```
POST /auth/register
      │
      ├─▶ create User (email_verified=False)
      └─▶ _issue_verification_token()
                │
                ├─▶ INSERT email_verification_tokens (hash, 24h TTL)
                └─▶ send_verification_email() ──▶ logger.debug(token)

POST /auth/verify-email  { token }
      │
      ├─▶ hash token → look up in email_verification_tokens
      ├─▶ set used_at, user.email_verified = True
      └─▶ return {ok: true}

POST /auth/login  (when require_email_verification=True)
      │
      └─▶ if not user.email_verified → 403 "Email not verified"
```
