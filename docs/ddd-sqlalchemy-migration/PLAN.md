---
goal: Refactor app to DDD-style architecture — replace SQLModel with SQLAlchemy 2.x ORM + Pydantic v2 schemas
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: amjadjibon
status: 'Planned'
tags: [refactor, architecture]
---

# DDD Refactor: SQLAlchemy 2.x + Pydantic v2

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

SQLModel collapses ORM models and API schemas into a single class, blurring the domain/infrastructure/presentation boundary. This refactor replaces SQLModel with pure SQLAlchemy 2.x ORM (for persistence) and Pydantic v2 `BaseModel` (for I/O schemas), then reorganises the code into DDD bounded contexts under `app/domain/`.

## 1. Requirements & Constraints

- **REQ-001**: All 18 ORM table classes must be converted to SQLAlchemy 2.x `DeclarativeBase` / `Mapped` / `mapped_column` style.
- **REQ-002**: All request/response schemas must inherit from `pydantic.BaseModel`, not `SQLModel`.
- **REQ-003**: Code is reorganised under `app/domain/<context>/` — one context per bounded concept (identity, session, mfa, rbac, oauth, social, api_key, audit).
- **REQ-004**: All existing HTTP routes, behaviour, and responses stay identical — this is a pure internal refactor.
- **CON-001**: `sqlmodel` is removed from `pyproject.toml` at the end; no SQLModel import may remain.
- **CON-002**: Alembic migrations are hand-written and must not be regenerated — existing migration files stay unchanged.
- **CON-003**: `uv run pytest tests/ -v` must pass at every phase boundary before committing.
- **GUD-001**: Use SQLAlchemy 2.x `Mapped[T]` type-annotated columns throughout — no `Column(...)` wrapper.
- **GUD-002**: Use `session.execute(select(...))` + `.scalar_one_or_none()` / `.scalars().all()` — not SQLModel's `session.exec()`.

## 2. Implementation Steps

> **Agent instructions**: After completing all tasks in a phase, run `uv run pytest tests/ -v` and confirm it passes, then `git add -u` (plus explicit paths for new files) and commit. Update checkboxes to `[x]` as each task is completed.

---

### Phase 1: Shared infrastructure base

**Goal**: Establish `Base = DeclarativeBase()` and migrate `AsyncSession` to pure SQLAlchemy before touching any model. All existing code continues to work after this phase.

- [ ] TASK-001: Create `app/shared/__init__.py` (empty).
- [ ] TASK-002: Create `app/shared/database.py` — define `Base = DeclarativeBase()`, export `engine` (copied from `app/core/db.py`), and `get_session` as an async generator yielding `AsyncSession` from `sqlalchemy.ext.asyncio`. Remove the `sqlmodel` import from `app/core/db.py` and import `AsyncSession` from `sqlalchemy.ext.asyncio` instead.
- [ ] TASK-003: Update `app/auth/deps.py` — change `from sqlmodel.ext.asyncio.session import AsyncSession` to `from sqlalchemy.ext.asyncio import AsyncSession`.
- [ ] TASK-004: Update `migrations/env.py` — replace `from sqlmodel import SQLModel` and `target_metadata = SQLModel.metadata` with `from app.shared.database import Base` and `target_metadata = Base.metadata`.
- [ ] TASK-005: Update `tests/conftest.py` — replace `from sqlmodel import SQLModel` with `from app.shared.database import Base`; change `SQLModel.metadata.create_all` → `Base.metadata.create_all` and `SQLModel.metadata.drop_all` → `Base.metadata.drop_all`.
- [ ] TASK-006: Update `main.py` — replace `from sqlmodel import SQLModel` with `from app.shared.database import Base`; change `SQLModel.metadata.create_all` → `Base.metadata.create_all`; add `import app.domain` noqa import once domain package exists (leave as TODO comment for now).

**Completion criteria**: `uv run pytest tests/ -v` passes (existing models still use SQLModel — the Base isn't used yet, but the session/metadata wiring is ready).

**git commit**: `git add -u && git commit -m "refactor: introduce shared database base and migrate AsyncSession to SQLAlchemy"`

---

### Phase 2: Identity domain — ORM entities

**Goal**: Convert the four identity-related ORM models to SQLAlchemy `Mapped` style and move them into `app/domain/identity/entities.py`.

- [ ] TASK-007: Create `app/domain/__init__.py` and `app/domain/identity/__init__.py` (both empty).
- [ ] TASK-008: Create `app/domain/identity/entities.py` — rewrite `User`, `PasswordResetToken`, `EmailVerificationToken`, and `PasswordHistory` as `Base`-derived SQLAlchemy models. Use `Mapped[T]` annotations and `mapped_column(...)` (no `sa_column=Column(...)` wrapper). Preserve all column names, types, constraints, indexes, and foreign keys exactly as in the current `app/auth/models.py` and `app/auth/db_models.py`.
- [ ] TASK-009: Update `app/auth/models.py` — replace the `SQLModel`-based `User` with a re-export: `from app.domain.identity.entities import User`. Keep the file so existing callers (`deps.py`, `admin/router.py`, etc.) are unaffected.
- [ ] TASK-010: Update `main.py` — replace `import app.auth.db_models` and `import app.auth.models` metadata registration imports with `import app.domain.identity.entities as _identity_entities  # noqa: F401`.
- [ ] TASK-011: Update `tests/conftest.py` — replace `import app.auth.db_models as _db_models` and `import app.auth.models as _models` with `import app.domain.identity.entities as _identity  # noqa: F401` (or import all domain entity modules as they are created in later phases).

**Completion criteria**: `uv run pytest tests/ -v` passes. The `user` table and token tables are created from `app.domain.identity.entities` via `Base.metadata`.

**git commit**: `git add -u app/domain/identity/entities.py app/domain/__init__.py app/domain/identity/__init__.py && git commit -m "refactor: migrate identity ORM models to SQLAlchemy DeclarativeBase"`

---

### Phase 3: Session, MFA, RBAC, Social domain entities

**Goal**: Convert the remaining ORM models group by group into domain entity files.

- [ ] TASK-012: Create `app/domain/session/__init__.py` and `app/domain/session/entities.py` — rewrite `UserSession` from `app/auth/db_models.py`.
- [ ] TASK-013: Create `app/domain/mfa/__init__.py` and `app/domain/mfa/entities.py` — rewrite `UserMfaSecret`, `UserMfaBackupCode`.
- [ ] TASK-014: Create `app/domain/rbac/__init__.py` and `app/domain/rbac/entities.py` — rewrite `Role`, `Permission`, `UserRole`, `RolePermission`.
- [ ] TASK-015: Create `app/domain/social/__init__.py` and `app/domain/social/entities.py` — rewrite `UserSocialAccount`.
- [ ] TASK-016: Update `main.py` — add noqa metadata-registration imports for each new domain entity module.

**Completion criteria**: `uv run pytest tests/ -v` passes. All four new entity tables appear in `Base.metadata`.

**git commit**: `git add -u && git commit -m "refactor: migrate session, mfa, rbac, social ORM models to domain entities"`

---

### Phase 4: OAuth, ApiKey, Audit domain entities

**Goal**: Migrate the remaining ORM models and delete `app/auth/db_models.py` once all models have moved.

- [ ] TASK-017: Create `app/domain/oauth/__init__.py` and `app/domain/oauth/entities.py` — rewrite `OAuthClient`, `OAuthAuthorizationCode`, `OAuthAccessToken`, `OAuthRefreshToken`.
- [ ] TASK-018: Create `app/domain/api_key/__init__.py` and `app/domain/api_key/entities.py` — rewrite `APIKey`.
- [ ] TASK-019: Create `app/domain/audit/__init__.py` and `app/domain/audit/entities.py` — rewrite `AuditLog`.
- [ ] TASK-020: Update `main.py` — add noqa imports for oauth/api_key/audit entity modules; remove the old `import app.auth.db_models` and `import app.auth.models` registration imports.
- [ ] TASK-021: Delete `app/auth/db_models.py` — all 17 models have moved; fix any remaining imports that still pointed to it (grep for `from app.auth.db_models import`).
- [ ] TASK-022: Delete `app/auth/models.py` — `User` now lives in `app.domain.identity.entities`; update all callers (`deps.py`, `admin/router.py`, `admin/services/user_management.py`, `scripts/seed_db.py`, `app/auth/repositories/user_repository.py`, `app/auth/services/auth_service.py`, `app/auth/services/social_service.py`) to import `User` from `app.domain.identity.entities`.

**Completion criteria**: `uv run pytest tests/ -v` passes. No file imports from `app.auth.db_models` or `app.auth.models`. `sqlmodel.Field` and `sqlmodel.SQLModel` are used only in `app/auth/schemas.py` and sub-module schema files.

**git commit**: `git add -u && git commit -m "refactor: migrate oauth, api_key, audit ORM models; delete old db_models and models modules"`

---

### Phase 5: Pydantic v2 schemas

**Goal**: Replace every `SQLModel`-based schema (non-table) with a `pydantic.BaseModel`. Move schemas into their domain context.

- [ ] TASK-023: Rewrite `app/auth/schemas.py` — replace all `class Foo(SQLModel):` with `class Foo(BaseModel):`. Replace `from sqlmodel import Field, SQLModel` with `from pydantic import BaseModel, Field`. All field validators, `model_config`, and `ConfigDict` usage stays identical (Pydantic v2 already handles these). Remove the `from sqlmodel import Field` import (use `pydantic.Field` directly).
- [ ] TASK-024: Create `app/domain/identity/schemas.py` — move the contents of `app/auth/schemas.py` here. Update `app/auth/schemas.py` to re-export from the new location so no router needs changing yet.
- [ ] TASK-025: Rewrite `app/auth/mfa/models.py` — replace `SQLModel` bases with `BaseModel`. Move to `app/domain/mfa/schemas.py`; add re-export in `app/auth/mfa/models.py`.
- [ ] TASK-026: Rewrite `app/auth/rbac/models.py` — move to `app/domain/rbac/schemas.py`; re-export.
- [ ] TASK-027: Rewrite `app/auth/sessions/models.py` — move to `app/domain/session/schemas.py`; re-export.
- [ ] TASK-028: Rewrite `app/auth/oauth/models.py` — move to `app/domain/oauth/schemas.py`; re-export.
- [ ] TASK-029: Rewrite `app/auth/api_keys/models.py` — move to `app/domain/api_key/schemas.py`; re-export.
- [ ] TASK-030: Rewrite `app/admin/models.py` — replace `SQLModel` bases with `BaseModel`.

**Completion criteria**: `uv run pytest tests/ -v` passes. No `SQLModel` import remains in any `*models.py` or `*schemas.py` file.

**git commit**: `git add -u && git commit -m "refactor: replace SQLModel schemas with Pydantic v2 BaseModel across all domains"`

---

### Phase 6: Repository and service layer — SQLAlchemy query API

**Goal**: Replace every `session.exec(select(...))`, `sqlmodel.select`, `sqlmodel.func`, and `sqlmodel.update` call with the SQLAlchemy 2.x equivalent (`session.execute`, `sqlalchemy.select`, etc.).

The key API change is:
- **Before** (SQLModel): `result = await session.exec(select(User).where(...))` → `user = result.first()`
- **After** (SQLAlchemy): `result = await session.execute(select(User).where(...))` → `user = result.scalar_one_or_none()`
- **Before**: `from sqlmodel import select, func, update`
- **After**: `from sqlalchemy import select, func, update`
- **Before**: `from sqlmodel.ext.asyncio.session import AsyncSession`
- **After**: `from sqlalchemy.ext.asyncio import AsyncSession`

Files to update (replace imports + query calls):
- [ ] TASK-031: `app/auth/repositories/user_repository.py`
- [ ] TASK-032: `app/auth/repositories/session_repository.py`
- [ ] TASK-033: `app/auth/repositories/oauth_repository.py`
- [ ] TASK-034: `app/auth/rbac/repositories/role_repository.py`
- [ ] TASK-035: `app/auth/rbac/repositories/permission_repository.py`
- [ ] TASK-036: `app/auth/api_keys/repository.py`
- [ ] TASK-037: `app/auth/services/mfa_service.py`
- [ ] TASK-038: `app/auth/services/session_service.py`
- [ ] TASK-039: `app/auth/services/oauth_service.py`
- [ ] TASK-040: `app/auth/services/social_service.py`
- [ ] TASK-041: `app/auth/security/password_history.py`
- [ ] TASK-042: `app/auth/audit/logger.py` and `app/auth/audit/reports.py`
- [ ] TASK-043: `app/admin/dashboard.py` and `app/admin/services/user_management.py`
- [ ] TASK-044: `app/auth/sessions/cleanup.py`
- [ ] TASK-045: All router files that use inline `from sqlmodel import select` — `app/auth/password/router.py`, `app/auth/verification/router.py`, `app/auth/social/router.py`, `app/auth/oauth/router.py`, `app/auth/audit/router.py`, `app/auth/rbac/router.py`, `app/admin/router.py`.
- [ ] TASK-046: `app/core/db.py` — remove any remaining `sqlmodel` import; confirm it only uses `sqlalchemy.ext.asyncio`.

**Completion criteria**: `grep -rn "sqlmodel" app/ --include="*.py"` returns zero results. `uv run pytest tests/ -v` passes.

**git commit**: `git add -u && git commit -m "refactor: replace sqlmodel query API with SQLAlchemy 2.x select/execute throughout"`

---

### Phase 7: Domain consolidation and cleanup

**Goal**: Move repositories and services into their domain packages, remove `sqlmodel` from `pyproject.toml`, and verify the full test suite.

- [ ] TASK-047: Move `app/auth/repositories/user_repository.py` → `app/domain/identity/repository.py`. Update all callers.
- [ ] TASK-048: Move `app/auth/repositories/session_repository.py` → `app/domain/session/repository.py`. Update callers.
- [ ] TASK-049: Move `app/auth/repositories/oauth_repository.py` → `app/domain/oauth/repository.py`. Update callers.
- [ ] TASK-050: Move `app/auth/rbac/repositories/role_repository.py` and `permission_repository.py` → `app/domain/rbac/repository.py`. Update callers.
- [ ] TASK-051: Move `app/auth/api_keys/repository.py` → `app/domain/api_key/repository.py`. Update callers.
- [ ] TASK-052: Move `app/auth/services/auth_service.py` → `app/domain/identity/service.py`. Update callers.
- [ ] TASK-053: Move `app/auth/services/session_service.py` → `app/domain/session/service.py`. Update callers.
- [ ] TASK-054: Move `app/auth/services/mfa_service.py` → `app/domain/mfa/service.py`. Update callers.
- [ ] TASK-055: Move `app/auth/services/oauth_service.py` → `app/domain/oauth/service.py`. Update callers.
- [ ] TASK-056: Move `app/auth/services/social_service.py` → `app/domain/social/service.py`. Update callers.
- [ ] TASK-057: Remove `sqlmodel` from `pyproject.toml` dependencies. Run `uv sync` to confirm no import error.
- [ ] TASK-058: Delete now-empty legacy directories: `app/auth/repositories/`, `app/auth/services/`, `app/auth/store.py` (delegate all shim callers to domain paths).

**Completion criteria**: `grep -rn "sqlmodel" . --include="*.py" | grep -v ".venv"` returns zero results. `uv run pytest tests/ -v` passes with 0 failures.

**git commit**: `git add -u && git commit -m "refactor: consolidate repositories and services into domain packages; remove sqlmodel dependency"`

---

## 3. Alternatives Considered

- **ALT-001**: SQLModel 0.0.38+ supports SQLAlchemy 2.x under the hood, so we could stay on SQLModel and just upgrade. Rejected — SQLModel still conflates ORM and schema concerns, which the DDD structure explicitly separates.
- **ALT-002**: Incremental replacement using `sqlmodel` as a shim for months. Rejected — the re-export pattern accumulates tech debt without a clear end date.
- **ALT-003**: Keep existing directory structure and only swap the base classes. Rejected — the value of DDD is in the bounded context organisation, not just the library choice.

## 4. Dependencies

- **DEP-001**: `sqlalchemy[asyncio]>=2.0` — already a transitive dependency via SQLModel; must be declared explicitly after SQLModel is removed.
- **DEP-002**: `pydantic>=2.0` — already present via `fastapi[standard]`.
- **DEP-003**: `aiosqlite` and `asyncpg` — remain as async dialect drivers; no change.

## 5. Affected Files

- **FILE-001**: `app/shared/database.py` — new; ORM Base + session factory
- **FILE-002**: `app/domain/*/entities.py` — new (8 files); replaces `app/auth/db_models.py` + `app/auth/models.py`
- **FILE-003**: `app/domain/*/schemas.py` — new (7 files); replaces `app/auth/schemas.py` and sub-module `models.py` files
- **FILE-004**: `app/domain/*/repository.py` — moved from `app/auth/repositories/` and `app/auth/rbac/repositories/`
- **FILE-005**: `app/domain/*/service.py` — moved from `app/auth/services/`
- **FILE-006**: `app/auth/db_models.py`, `app/auth/models.py`, `app/auth/store.py` — deleted
- **FILE-007**: `pyproject.toml` — remove `sqlmodel`; add explicit `sqlalchemy[asyncio]>=2.0`
- **FILE-008**: `migrations/env.py`, `tests/conftest.py`, `main.py` — metadata wiring update

## 6. Testing

- [ ] TEST-001: `uv run pytest tests/ -v` passes at each phase boundary before committing.
- [ ] TEST-002: After Phase 6, run `grep -rn "sqlmodel" app/ --include="*.py"` — must return zero lines.
- [ ] TEST-003: After Phase 7, run `uv run pytest tests/ -v` on a fresh SQLite DB (delete the test DB and re-run) to confirm `Base.metadata.create_all` produces the correct schema.
- [ ] TEST-004: After Phase 7, run `uv run alembic upgrade head` against a PostgreSQL instance (or Docker) to confirm migrations still apply cleanly.

## 7. Risks & Assumptions

- **RISK-001**: SQLModel's `session.exec()` returns a different result type from SQLAlchemy's `session.execute()` — `.first()` vs `.scalar_one_or_none()`. Every repository call must be audited. Mitigation: Phase 6 updates all queries systematically by file, with tests after each file change.
- **RISK-002**: SQLAlchemy `Mapped[]` columns cannot use `server_default` as a Python `str` for boolean — must use `sqlalchemy.text("0")` or `sqlalchemy.false()`. Mitigation: documented in entity conversion tasks.
- **RISK-003**: Alembic `env.py` uses `target_metadata` to generate migrations. After switching to `Base.metadata`, all domain entity modules must be imported before `env.py` runs — otherwise Alembic will generate a migration that drops all tables. Mitigation: TASK-004 adds explicit imports for all entity modules in `env.py`.
- **ASSUMPTION-001**: `sqlalchemy[asyncio]>=2.0` is already installed transitively via SQLModel; explicit pinning in pyproject.toml is a declaration change only, not a new install.

## 8. Architecture Diagram

```
Before                               After
──────────────────────────────────   ──────────────────────────────────────────
app/                                 app/
├── auth/                            ├── core/          (unchanged)
│   ├── models.py     ← SQLModel     ├── shared/
│   ├── db_models.py  ← SQLModel     │   └── database.py  ← Base, engine, session
│   ├── schemas.py    ← SQLModel     ├── domain/
│   ├── store.py                     │   ├── identity/
│   ├── repositories/                │   │   ├── entities.py  ← SQLAlchemy
│   ├── services/                    │   │   ├── schemas.py   ← Pydantic BaseModel
│   ├── mfa/                         │   │   ├── repository.py
│   ├── rbac/                        │   │   └── service.py
│   ├── oauth/                       │   ├── session/
│   ├── social/                      │   ├── mfa/
│   ├── sessions/                    │   ├── rbac/
│   ├── api_keys/                    │   ├── oauth/
│   └── audit/                       │   ├── social/
├── admin/                           │   ├── api_key/
└── core/                            │   └── audit/
                                     ├── auth/          (routers only — presentation)
                                     └── admin/         (routers only — presentation)
```
