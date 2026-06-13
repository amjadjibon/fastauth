---
goal: Redis JTI blocklist so access tokens can be invalidated before expiry on logout
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: amjadjibon
status: 'In progress'
tags: [feature, architecture]
---

# Access Token Revocation (JTI Blocklist)

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

Refresh tokens are already tied to `UserSession` rows (via `refresh_token_jti`) and can be revoked by setting `revoked_at`. Access tokens are stateless JWTs with no server-side revocation path — once issued they are valid until expiry (`access_token_expire_seconds`, default 60s). For logout to be instantaneous, the access token's JTI must be added to a Redis blocklist that `decode_token` checks on every request.

## 1. Requirements & Constraints

- **REQ-001**: After `POST /auth/logout`, the caller's access token must be rejected with 401 for its remaining lifetime.
- **REQ-002**: Blocklist entries expire automatically at the token's `exp` — no manual cleanup needed.
- **CON-001**: If Redis is unavailable, fall back gracefully: log a warning and allow the request rather than causing an outage. Revocation is best-effort without Redis.
- **SEC-001**: Access token `jti` must be a random UUID generated at token creation time (add if not already present).
- **GUD-001**: Redis key pattern: `jti:blocked:{jti}`, TTL = token `exp - now` seconds.

## 2. Implementation Steps

> **Agent instructions**: This repo uses git. Use `git add -A && git commit -m "<message>"` at each phase boundary. Update checkboxes to `[x]` as each task is completed.

### Phase 1: JTI in Access Tokens

**Goal**: Ensure every access token contains a `jti` claim that can be used as a blocklist key.

- [x] TASK-001: In `app/core/security.py`, find `create_token`. If `jti` is not already added to the payload, add `"jti": str(uuid.uuid4())` before signing.
  > Resolved by: Added `jti` in `make_tokens` in `app/auth/deps.py` (where access/refresh tokens are created together) rather than `create_token`, since `create_token` is generic and `jti` is specific to access tokens.
- [x] TASK-002: In `decode_token`, return the `jti` claim alongside the existing payload dict, or ensure callers can extract it from the returned dict.
  > `decode_token` already returns the full payload dict; callers read `payload.get("jti")` directly. No change needed.

**Completion criteria**: `create_token({"sub": "test"})` decoded with `decode_token` contains a `jti` key.

**git commit**: `git add -A && git commit -m "feat: add jti claim to access tokens"`

---

### Phase 2: Blocklist Read/Write

**Goal**: Implement the two blocklist operations: block a JTI and check if a JTI is blocked.

- [x] TASK-003: Create `app/core/token_blocklist.py` with two functions:
  - `async def block_token(jti: str, ttl_seconds: int) -> None` — sets `jti:blocked:{jti}` in Redis with the given TTL; no-ops silently if Redis is not configured.
  - `async def is_blocked(jti: str) -> bool` — returns `True` if the key exists; returns `False` on Redis error (log warning, fail open).
- [x] TASK-004: Import and use the same Redis client used by the rate limiter (`app/core/limiter.py` exports `get_redis`).
  > Added `get_redis()` accessor to `limiter.py`; `token_blocklist.py` imports and uses it.

**Completion criteria**: Unit test (no HTTP): `block_token("abc", 10)` followed by `is_blocked("abc")` returns `True`; `is_blocked("xyz")` returns `False`.

**git commit**: `git add -A && git commit -m "feat: implement Redis JTI blocklist for access token revocation"`

---

### Phase 3: Wire Blocklist into Auth Flow

**Goal**: Block on logout; check on every authenticated request.

- [x] TASK-005: In `app/auth/router.py` `logout` handler, after revoking the session, extract the `jti` from the current access token and call `block_token(jti, remaining_ttl)` where `remaining_ttl = max(0, token_exp - now)`.
- [x] TASK-006: In `app/auth/deps.py`, in the dependency that validates the Bearer token, after `decode_token` succeeds, call `await is_blocked(payload["jti"])`; if `True`, raise `HTTPException(401, "Token has been revoked")`.

**Completion criteria**: Integration test — login → logout → `GET /auth/me` with the old access token returns 401.

**git commit**: `git add -A && git commit -m "feat: enforce JTI blocklist on logout and per-request token validation"`

---

### Phase 4: Integration Test

**Goal**: Prove the revocation path works end-to-end.

- [ ] TASK-007: Add `tests/test_token_revocation.py`: login → capture access token → logout → `GET /auth/me` with old token → assert 401 with `"Token has been revoked"`.
- [ ] TASK-008: Add test: token still valid before logout — `GET /auth/me` returns 200 before calling logout.
- [ ] TASK-009: Add test for Redis-absent fallback: mock `get_redis()` to return `None`; logout succeeds (no crash); old token is NOT rejected (fail-open documented in response).

**Completion criteria**: `uv run pytest tests/test_token_revocation.py -v` — all tests pass.

**git commit**: `git add -A && git commit -m "test: access token revocation integration tests"`

---

## 3. Alternatives Considered

- **ALT-001**: Short access token lifetime only (no blocklist) — rejected because 60s window is unacceptable for security-sensitive logout; and reducing to <5s hurts UX.
- **ALT-002**: Store blocklist in PostgreSQL — rejected because it adds a DB round-trip on every request; Redis `GET` is O(1) and sub-millisecond.

## 4. Dependencies

- **DEP-001**: Redis — already in `compose.yaml`; `settings.redis_url` is optional.
- **DEP-002**: `redis.asyncio` — already imported in `main.py`.

## 5. Affected Files

- **FILE-001**: `app/core/security.py` — add `jti` to `create_token`
- **FILE-002**: `app/core/token_blocklist.py` — new, blocklist read/write
- **FILE-003**: `app/auth/router.py` — call `block_token` in logout
- **FILE-004**: `app/auth/deps.py` — call `is_blocked` in Bearer validation
- **FILE-005**: `tests/test_token_revocation.py` — new

## 6. Testing

- [ ] TEST-001: `uv run pytest tests/test_token_revocation.py -v` — all pass.
- [ ] TEST-002: Manual: start stack with Redis, login, logout, reuse token → 401.
- [ ] TEST-003: Manual: start stack without Redis (`REDIS_URL=` unset), login, logout → no 500 error.

## 7. Risks & Assumptions

- **RISK-001**: If Redis restarts during the token's lifetime, all blocklist entries are lost and revoked tokens become valid again — mitigation: use Redis persistence (`appendonly yes`) in production.
- **ASSUMPTION-001**: `app/core/limiter.py` exports a `get_redis()` function that returns the shared async Redis client; if not, create a module-level accessor in `app/core/token_blocklist.py`.

## 8. Architecture Diagram

```
POST /auth/logout
       │
       ├──▶ revoke UserSession (DB)
       └──▶ block_token(jti, ttl)  ──SET jti:blocked:{jti} EX ttl──▶  Redis

GET /auth/me  (any authenticated route)
       │
       ▼
  decode_token()  ──▶  is_blocked(jti)  ──GET jti:blocked:{jti}──▶  Redis
       │                    │
       │                  True  ──▶  401 Token has been revoked
       └── False ──▶  proceed
```

## 9. Related Specs & Further Reading

- `app/core/security.py` — `create_token`, `decode_token`
- `app/auth/deps.py` — Bearer token dependency
- `app/auth/router.py` — logout handler
- `app/core/limiter.py` — existing Redis client accessor
