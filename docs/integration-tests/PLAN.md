---
goal: pytest integration tests for RBAC, session management, and MFA flows
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: amjadjibon
status: 'Planned'
tags: [feature, chore]
---

# Integration Tests: RBAC, Sessions, and MFA

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Extend the pytest suite with end-to-end coverage for three flows that have no dedicated tests: RBAC role/permission enforcement, session lifecycle (revocation, refresh-after-revoke), and MFA setup-to-verify. The existing `conftest.py` uses an in-memory SQLite client — all new tests follow the same pattern.

## 1. Requirements & Constraints

- **REQ-001**: Tests must run via `uv run pytest` with no external services (SQLite in-memory, no Redis).
- **REQ-002**: Each test file is independent; no shared state between test modules.
- **CON-001**: Do not modify `conftest.py` — add module-level fixtures where extra setup is needed.
- **GUD-001**: Use `pytest-asyncio` with `loop_scope="session"` to match existing style.
- **GUD-002**: Seed data (admin user, roles) via the HTTP API, not direct DB inserts, to test the full stack.

## 2. Implementation Steps

> **Agent instructions**: This repo uses git. Use `git add -A && git commit -m "<message>"` at each phase boundary. Update checkboxes to `[x]` as each task is completed.

### Phase 1: RBAC Integration Tests

**Goal**: Verify that role assignment, role enforcement, and permission checks work end-to-end via HTTP.

- [ ] TASK-001: Create `tests/test_rbac_integration.py`. Add a module-level fixture that registers two users (a regular user and one promoted to admin via `POST /auth/roles/{role_id}/users`) and yields both clients.
- [ ] TASK-002: Test `GET /auth/roles` returns 200 for any authenticated user and lists at least the seeded `admin` and `user` system roles.
- [ ] TASK-003: Test `POST /auth/roles` with a non-admin token returns 403; with admin token returns 201 and the role is visible in `GET /auth/roles`.
- [ ] TASK-004: Test `DELETE /auth/roles/{role_id}` on a system role returns 400 (`Cannot modify system roles`).
- [ ] TASK-005: Test `POST /auth/roles/{role_id}/permissions` assigns a permission to the role and `GET /auth/me` for a user with that role lists the permission under `permissions`.

**Completion criteria**: `uv run pytest tests/test_rbac_integration.py -v` — all tests pass, no skips.

**git commit**: `git add -A && git commit -m "test: add RBAC integration tests"`

---

### Phase 2: Session Lifecycle Integration Tests

**Goal**: Verify session list, per-session revocation, and that a revoked refresh token cannot be reused.

**Depends on**: Phase 1 complete (conftest pattern established)

- [ ] TASK-006: Create `tests/test_sessions_integration.py`. Login a user, capture `refresh_token`; assert `GET /auth/sessions` returns 1 active session.
- [ ] TASK-007: Test `DELETE /auth/sessions/{session_id}` on the active session returns 204; follow-up `POST /auth/refresh` with the now-revoked token returns 401.
- [ ] TASK-008: Test `DELETE /auth/sessions` (revoke all) clears all sessions; a second call to `GET /auth/sessions` returns an empty list.
- [ ] TASK-009: Test concurrent sessions: login twice, assert `GET /auth/sessions` shows 2 entries; revoke one; confirm the other refresh token still works.

**Completion criteria**: `uv run pytest tests/test_sessions_integration.py -v` — all tests pass.

**git commit**: `git add -A && git commit -m "test: add session lifecycle integration tests"`

---

### Phase 3: MFA Flow Integration Tests

**Goal**: Cover TOTP enroll → verify → login-with-MFA → backup-code paths.

**Depends on**: Phase 1 complete

- [ ] TASK-010: Create `tests/test_mfa_flow.py`. Add a helper that calls `POST /auth/mfa/setup` and extracts the TOTP secret from the response.
- [ ] TASK-011: Test full enroll flow: setup → `POST /auth/mfa/verify` with a valid TOTP code → `GET /auth/me` shows `mfa_enabled: true`.
- [ ] TASK-012: Test login with MFA enabled: `POST /auth/login` returns `mfa_required: true` and a `mfa_session_token`; `POST /auth/mfa/login` with valid TOTP returns access/refresh tokens.
- [ ] TASK-013: Test backup code: after enrollment, `POST /auth/mfa/login` with a backup code returns tokens; same code used a second time returns 401.
- [ ] TASK-014: Test `POST /auth/mfa/disable` with valid TOTP removes MFA; subsequent login returns tokens directly without MFA step.

**Completion criteria**: `uv run pytest tests/test_mfa_flow.py -v` — all tests pass.

**git commit**: `git add -A && git commit -m "test: add MFA flow integration tests"`

---

### Phase 4: CI Wiring

**Goal**: Ensure new tests run in the existing GitHub Actions CI workflow.

- [ ] TASK-015: Verify `.github/workflows/` has a step that runs `uv run pytest` — if it targets specific paths, add the three new test files (or widen the glob to `tests/test_*.py`).
- [ ] TASK-016: Run `uv run pytest tests/ -v --tb=short` locally; confirm all existing tests still pass alongside the new ones.

**Completion criteria**: `uv run pytest tests/ -v` exits 0 with no failures.

**git commit**: `git add -A && git commit -m "chore: ensure new integration tests run in CI"`

---

## 3. Alternatives Considered

- **ALT-001**: Use a shared PostgreSQL container for tests — rejected because SQLite in-memory is faster and sufficient; PostgreSQL-specific SQL is only in the seed script.
- **ALT-002**: Use factory-boy for test data — rejected because the HTTP API is the right fixture source for integration tests.

## 4. Dependencies

- **DEP-001**: `pytest-asyncio` — already in dev dependencies.
- **DEP-002**: `httpx` — already used in `conftest.py`.
- **DEP-003**: `pyotp` — needed in `tests/test_mfa_flow.py` to generate valid TOTP codes; add to dev dependencies if not present.

## 5. Affected Files

- **FILE-001**: `tests/test_rbac_integration.py` — new
- **FILE-002**: `tests/test_sessions_integration.py` — new
- **FILE-003**: `tests/test_mfa_flow.py` — new
- **FILE-004**: `pyproject.toml` — add `pyotp` to test dependencies if missing

## 6. Testing

- [ ] TEST-001: `uv run pytest tests/test_rbac_integration.py tests/test_sessions_integration.py tests/test_mfa_flow.py -v` — all pass.
- [ ] TEST-002: `uv run pytest tests/ -v` — full suite passes, no regressions.

## 7. Risks & Assumptions

- **RISK-001**: MFA router path names may differ from `POST /auth/mfa/setup` — mitigation: verify paths in `app/auth/mfa/router.py` before writing tests.
- **ASSUMPTION-001**: The seeded `admin` and `user` roles exist in the SQLite in-memory DB after `create_all` (they are inserted via Alembic `data` migrations in PostgreSQL but may need manual seeding in SQLite tests).

## 8. Architecture Diagram

```
Tests (httpx AsyncClient)
        │
        ▼
FastAPI app (ASGITransport, SQLite in-memory)
        │
   ┌────┴──────┐
   │  Auth API │
   │  RBAC API │
   │  MFA API  │
   │  Sessions │
   └────┬──────┘
        │
   SQLite :memory:
```

## 9. Related Specs & Further Reading

- `tests/conftest.py` — base client fixture
- `app/auth/rbac/router.py` — RBAC endpoints
- `app/auth/sessions/router.py` — session endpoints
- `app/auth/mfa/router.py` — MFA endpoints
- `docs/auth-hardening/PLAN.md` — prior security work
