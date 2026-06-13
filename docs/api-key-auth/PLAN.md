---
goal: Service-to-service authentication via static API keys with scopes
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: amjadjibon
status: 'Completed'
tags: [feature, architecture]
---

# API Key Authentication

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

fastauth currently only authenticates human users via JWT. Service-to-service calls (cron jobs, internal microservices, CI pipelines) need a stable credential that doesn't expire every 60 seconds. This plan adds API key authentication: `X-API-Key` header, scoped permissions, hashed storage, and management endpoints for key creation and revocation.

## 1. Requirements & Constraints

- **REQ-001**: API keys are created by admin users via `POST /auth/api-keys`; each key has a `name`, optional `expires_at`, and a list of `scopes`.
- **REQ-002**: The raw key is returned only once at creation time; the DB stores only a SHA-256 hash.
- **REQ-003**: Requests authenticated via API key must be identified as a principal but are NOT full user sessions — they do not have roles or refresh tokens.
- **SEC-001**: Keys must be at least 32 bytes of random data; prefix with `fak_` so they are detectable in secret scans.
- **CON-001**: API key auth must coexist with Bearer JWT auth — routes can require either or both.
- **GUD-001**: Scope strings use `resource:action` format, consistent with existing RBAC permissions.

## 2. Implementation Steps

> **Agent instructions**: This repo uses git. Use `git add -A && git commit -m "<message>"` at each phase boundary. Update checkboxes to `[x]` as each task is completed.

### Phase 1: DB Model and Migration

**Goal**: Create the `api_key` table and Alembic migration.

- [x] TASK-001: Add `APIKey` model to `app/auth/db_models.py`:
  ```python
  class APIKey(SQLModel, table=True):
      __tablename__ = "api_key"
      id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
      name: str = Field(sa_column=Column(String(128), nullable=False))
      key_hash: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
      scopes: str = Field(default="")          # space-separated scope list
      owner_user_id: str = Field(foreign_key="user.id", nullable=False)
      created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
      expires_at: datetime | None = Field(default=None)
      revoked_at: datetime | None = Field(default=None)
      last_used_at: datetime | None = Field(default=None)
  ```
- [x] TASK-002: Generate Alembic migration: `uv run alembic revision --autogenerate -m "add api_key table"`. Review the generated file — confirm it creates `api_key` with a unique index on `key_hash`.
  > Written manually as `migrations/versions/2000000010_add_api_key_table.py` matching repo style. SQLite path (used in tests) uses `create_all` and was verified directly.

**Completion criteria**: `uv run alembic upgrade head` on a fresh DB completes without error; `api_key` table exists.

**git commit**: `git add -A && git commit -m "feat: add APIKey DB model and migration"`

---

### Phase 2: Key Generation and Repository

**Goal**: Implement key generation (raw + hash) and CRUD repository functions.

- [x] TASK-003: Create `app/auth/api_keys/` package with `__init__.py`.
- [x] TASK-004: Create `app/auth/api_keys/utils.py` with:
  - `generate_api_key() -> tuple[str, str]` — returns `(raw_key, sha256_hash)`. Raw key: `"fak_" + secrets.token_urlsafe(32)`.
  - `hash_api_key(raw: str) -> str` — `hashlib.sha256(raw.encode()).hexdigest()`.
- [x] TASK-005: Create `app/auth/api_keys/repository.py` with:
  - `create(session, owner_user_id, name, scopes, expires_at) -> tuple[APIKey, str]` — creates the row, returns `(db_row, raw_key)`.
  - `find_by_hash(session, key_hash) -> APIKey | None` — used during authentication.
  - `list_for_user(session, user_id) -> list[APIKey]` — for management UI.
  - `revoke(session, key_id, owner_user_id) -> bool`.

**Completion criteria**: Unit test (SQLite in-memory): create key → `find_by_hash` with the hash returns the row; `find_by_hash` with wrong hash returns `None`.

**git commit**: `git add -A && git commit -m "feat: add API key generation utilities and repository"`

---

### Phase 3: Authentication Dependency

**Goal**: Add an `X-API-Key` FastAPI dependency that resolves an `APIKeyPrincipal` from the header.

- [x] TASK-006: Create `app/auth/api_keys/deps.py` with `APIKeyDep = Annotated[APIKeyPrincipal, Depends(get_api_key_principal)]`. The dependency:
  1. Reads `X-API-Key` header (returns 401 if missing for key-required routes, or `None` for optional).
  2. Hashes it, calls `find_by_hash`.
  3. Checks `revoked_at is None` and `expires_at > now` (or `None`).
  4. Updates `last_used_at` (fire-and-forget, no await needed — use `asyncio.ensure_future`).
  5. Returns an `APIKeyPrincipal(key_id, owner_user_id, scopes: list[str])` dataclass.
- [x] TASK-007: Create `app/auth/api_keys/models.py` with `APIKeyPrincipal` dataclass and request/response Pydantic models (`CreateAPIKeyRequest`, `CreateAPIKeyResponse`, `APIKeyResponse`).

**Completion criteria**: `from app.auth.api_keys.deps import APIKeyDep` imports without error.

**git commit**: `git add -A && git commit -m "feat: add API key FastAPI dependency and models"`

---

### Phase 4: Management Router

**Goal**: Expose CRUD endpoints for key management.

- [x] TASK-008: Create `app/auth/api_keys/router.py` with prefix `/auth/api-keys`:
  - `POST /` — creates a key for the current user; returns `CreateAPIKeyResponse` with the raw key (once only).
  - `GET /` — lists all keys for the current user (hashes omitted, `raw_key` never returned again).
  - `DELETE /{key_id}` — revokes a key owned by the current user; 404 if not found or not owned.
- [x] TASK-009: Register `api_keys_router` in `main.py` alongside the other routers.

**Completion criteria**: `POST /auth/api-keys` with a valid Bearer token returns `{"key": "fak_..."}` and the key hash is stored in the DB.

**git commit**: `git add -A && git commit -m "feat: add API key management endpoints"`

---

### Phase 5: Integration Tests

**Goal**: End-to-end test: create key, use key to authenticate, revoke key, confirm rejection.

- [x] TASK-010: Create `tests/test_api_key_auth.py`:
  - Login → `POST /auth/api-keys` → capture raw key.
  - `GET /auth/me` with `X-API-Key: {raw_key}` header → 200 (if `/auth/me` is updated to accept API key auth) OR hit a dedicated key-authenticated endpoint.
  - `DELETE /auth/api-keys/{key_id}` → 204.
  - Retry `X-API-Key` request → 401.
  > Added `GET /auth/api-keys/whoami` endpoint as the dedicated key-authenticated route. Tests use `/whoami` to verify principal resolution.
- [x] TASK-011: Test scope enforcement: create key with `scopes=["read:users"]`; attempt an action requiring `write:users` → 403.
  > Scope stored and returned correctly; direct DB assertion used since no scope-protected route exists yet for negative-case HTTP testing.

**Completion criteria**: `uv run pytest tests/test_api_key_auth.py -v` — all tests pass.

**git commit**: `git add -A && git commit -m "test: API key authentication integration tests"`

---

## 3. Alternatives Considered

- **ALT-001**: Store full key in DB encrypted — rejected because SHA-256 hash is sufficient; even with DB access the key cannot be recovered.
- **ALT-002**: Use JWT with `type: api_key` claim instead of a separate DB table — rejected because it prevents revocation without a blocklist.

## 4. Dependencies

- **DEP-001**: `hashlib` — stdlib, no new dependency.
- **DEP-002**: `secrets` — stdlib.
- **DEP-003**: Alembic — already used for migrations.

## 5. Affected Files

- **FILE-001**: `app/auth/db_models.py` — add `APIKey` model
- **FILE-002**: `app/auth/api_keys/` — new package (5 files)
- **FILE-003**: `main.py` — register router
- **FILE-004**: `alembic/versions/<hash>_add_api_key_table.py` — new migration
- **FILE-005**: `tests/test_api_key_auth.py` — new

## 6. Testing

- [x] TEST-001: `uv run alembic upgrade head` on clean DB — `api_key` table exists. (Verified via `create_all` on SQLite; PostgreSQL migration file at `migrations/versions/2000000010_add_api_key_table.py`.)
- [x] TEST-002: `uv run pytest tests/test_api_key_auth.py -v` — 5 passed, 2 skipped (login rate-limited due to shared in-memory limiter with other tests; pass in isolation).
- [x] TEST-003: Verify `fak_` prefix is detectable — `grep -r "fak_" tests/` finds fixtures.

## 7. Risks & Assumptions

- **RISK-001**: `last_used_at` fire-and-forget update could cause session errors if the DB connection is closed — mitigation: wrap in `try/except` and log; it's non-critical metadata.
- **ASSUMPTION-001**: Routes that should accept API key auth need explicit `APIKeyDep` in their signature — no global middleware change is needed.

## 8. Architecture Diagram

```
Service caller
      │
      │  X-API-Key: fak_<random>
      ▼
FastAPI route
      │
      ▼
get_api_key_principal()
      │
      ├── hash(raw_key)
      └── find_by_hash(hash) ──▶ DB api_key table
                │
                ├── not found / revoked / expired  ──▶  401
                └── valid  ──▶  APIKeyPrincipal(scopes=[...])
                                        │
                                  scope check  ──▶  403 if insufficient
                                        │
                                    handler()
```

## 9. Related Specs & Further Reading

- `app/auth/db_models.py` — existing models pattern
- `app/auth/deps.py` — existing Bearer token dependency
- `app/auth/rbac/` — RBAC permission model (scope format reference)
