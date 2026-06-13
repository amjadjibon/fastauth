---
goal: Add OpenAPI request/response examples to FastAPI routes so the auto-generated docs are usable as a reference
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: amjadjibon
status: 'In progress'
tags: [chore, feature]
---

# OpenAPI Examples

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

The FastAPI-generated `/docs` and `/redoc` endpoints show schemas but no example values, so developers integrating with fastauth must read source code to understand request shapes. This plan adds concrete `openapi_examples` (or `model_config` examples) to all major request/response models and a few key route-level response examples for error cases.

## 1. Requirements & Constraints

- **REQ-001**: Every public-facing request body must have at least one named example.
- **REQ-002**: Every public-facing response model must have a `model_config` with `json_schema_extra.example`.
- **CON-001**: Do not add examples to internal/admin-only models; focus on `app/auth/models.py`, `app/auth/mfa/models.py`, `app/auth/rbac/models.py`, and `app/auth/sessions/models.py`.
- **GUD-001**: Use `openapi_examples` parameter on `Body(...)` for routes with multiple example variants (success path + error path). Use `json_schema_extra` on the model for single-example cases — simpler and co-located with the schema.
- **GUD-002**: Examples must be realistic but never real credentials — use `user@example.com`, `MyP@ssw0rd!`, `loadtest` style values.

## 2. Implementation Steps

> **Agent instructions**: This repo uses git. Use `git add -A && git commit -m "<message>"` at each phase boundary. Update checkboxes to `[x]` as each task is completed.

### Phase 1: Core Auth Models

**Goal**: Add examples to register, login, refresh, and token response models in `app/auth/models.py`.

- [x] TASK-001: Add `model_config = ConfigDict(json_schema_extra={"example": {...}})` to `RegisterRequest` with `username: "alice"`, `email: "alice@example.com"`, `password: "MyP@ssw0rd!"`.
- [x] TASK-002: Add example to `LoginRequest`: `username: "alice"`, `password: "MyP@ssw0rd!"`.
- [x] TASK-003: Add example to `TokenResponse`: `access_token: "<jwt>"`, `refresh_token: "<jwt>"`, `token_type: "bearer"`.
- [x] TASK-004: Add example to `RefreshRequest`: `refresh_token: "<jwt>"`.
- [x] TASK-005: Add example to `RegisterResponse`: `user_id: "00000000-0000-0000-0000-000000000001"`.
- [x] TASK-006: Add example to `UserResponse`: all fields populated with realistic values including `roles: ["user"]`, `permissions: ["read:profile"]`.
  > Note: `UserResponse` in `app/auth/models.py` does not have `roles` or `permissions` fields; omitted those from the example.
- [x] TASK-007: Add example to `ChangePasswordRequest`, `ForgotPasswordRequest`, `ResetPasswordRequest`.

**Completion criteria**: `GET /openapi.json` — `RegisterRequest` schema contains an `example` key. Visually verify in `GET /docs` that the "Try it out" form pre-populates with the example values.

**git commit**: `git add -A && git commit -m "docs: add OpenAPI examples to core auth request/response models"`

---

### Phase 2: MFA and Session Models

**Goal**: Add examples to MFA and session models.

**Depends on**: Phase 1 complete (pattern established)

- [ ] TASK-008: Add example to `MfaLoginRequest` in `app/auth/mfa/models.py`: `mfa_session_token: "<token>"`, `totp_code: "123456"`.
- [ ] TASK-009: Add example to MFA setup response model (whatever `POST /auth/mfa/setup` returns) with `secret: "BASE32SECRET"`, `qr_code_url: "otpauth://..."`.
- [ ] TASK-010: Add example to `SessionResponse` in `app/auth/sessions/models.py`: all device fields populated.
- [ ] TASK-011: Add example to `SessionsListResponse`.

**Completion criteria**: MFA and session models show examples in `/docs`.

**git commit**: `git add -A && git commit -m "docs: add OpenAPI examples to MFA and session models"`

---

### Phase 3: RBAC Models

**Goal**: Add examples to role and permission management models.

- [ ] TASK-012: Add examples to `CreateRoleRequest`, `RoleResponse`, `UpdateRoleRequest` in `app/auth/rbac/models.py`.
- [ ] TASK-013: Add examples to `AssignPermissionRequest`, `PermissionResponse`.
- [ ] TASK-014: Add examples to `AssignRoleRequest`.

**Completion criteria**: RBAC models show examples in `/docs`.

**git commit**: `git add -A && git commit -m "docs: add OpenAPI examples to RBAC models"`

---

### Phase 4: Route-Level Error Response Examples

**Goal**: Document common error responses (409, 401, 429) on the key routes so integrators know the error shape.

- [ ] TASK-015: In `app/auth/router.py`, add `responses` dict to `POST /register`: `{409: {"description": "Username taken", "content": {"application/json": {"example": {"detail": "Username already taken"}}}}}`.
- [ ] TASK-016: Add `responses` to `POST /login`: `{401: {"description": "Invalid credentials"}, 429: {"description": "Rate limited"}}`.
- [ ] TASK-017: Add `responses` to `POST /refresh`: `{401: {"description": "Invalid or revoked refresh token"}}`.

**Completion criteria**: `/openapi.json` for `/auth/register` includes a `409` response schema. Visible in `/redoc` sidebar.

**git commit**: `git add -A && git commit -m "docs: add error response schemas to register, login, and refresh routes"`

---

## 3. Alternatives Considered

- **ALT-001**: Separate `openapi.json` override file — rejected because it diverges from code and goes stale.
- **ALT-002**: Sphinx / MkDocs external docs — rejected because FastAPI's built-in `/docs` is already deployed and needs to be the source of truth.

## 4. Dependencies

- **DEP-001**: Pydantic v2 `ConfigDict` — already in use throughout the codebase.
- **DEP-002**: No new packages needed.

## 5. Affected Files

- **FILE-001**: `app/auth/models.py` — examples on 7 models
- **FILE-002**: `app/auth/mfa/models.py` — examples on 2 models
- **FILE-003**: `app/auth/sessions/models.py` — examples on 2 models
- **FILE-004**: `app/auth/rbac/models.py` — examples on 5 models
- **FILE-005**: `app/auth/router.py` — `responses` dicts on 3 routes

## 6. Testing

- [ ] TEST-001: `curl -s http://localhost:8000/openapi.json | jq '.components.schemas.RegisterRequest.example'` returns a non-null object.
- [ ] TEST-002: Open `http://localhost:8000/docs`, click "Try it out" on `POST /auth/register` — form pre-populates with the example values.
- [ ] TEST-003: `curl -s http://localhost:8000/openapi.json | jq '.paths."/auth/register".post.responses."409"'` returns a non-null object.

## 7. Risks & Assumptions

- **RISK-001**: Some models may use `SQLModel` directly without `model_config` support — use `class Config` style instead if `ConfigDict` is not available on those models.
- **ASSUMPTION-001**: `UserResponse` is the model returned by `GET /auth/me` — verify in `app/auth/router.py` before adding the example.

## 8. Architecture Diagram

```
Pydantic model
  model_config = ConfigDict(
    json_schema_extra={"example": {...}}
  )
        │
        ▼
FastAPI  /openapi.json  (auto-generated)
        │
   ┌────┴────┐
   │  /docs  │  ← Swagger UI (Try it out pre-fills example)
   │ /redoc  │  ← ReDoc (shows example in schema panel)
   └─────────┘
```

## 9. Related Specs & Further Reading

- `app/auth/models.py` — core auth models
- `app/auth/mfa/models.py` — MFA models
- `app/auth/rbac/models.py` — RBAC models
- [FastAPI response examples docs](https://fastapi.tiangolo.com/tutorial/schema-extra-example/)
