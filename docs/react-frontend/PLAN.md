---
goal: React/TypeScript SPA frontend replacing Jinja2 templates
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: Amjad Hossain
status: 'Completed'
tags: [feature, architecture]
---

# React Frontend — FastAuth SPA

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

Replace the four Jinja2 templates with a proper React 19 SPA at `./frontend`. The new frontend uses TanStack Router for type-safe routing, TanStack Query for server state, Zod for form validation, and Tailwind CSS v4 with the existing dark theme. Tokens are stored in memory (never `localStorage`) and refreshed transparently via an Axios interceptor.

## 1. Requirements & Constraints

- **REQ-001**: Pages: Login, Register, Verify Email (token confirm), Forgot Password, Reset Password, Dashboard, Admin Dashboard.
- **REQ-002**: Protected routes redirect to `/login` when unauthenticated; admin routes require `admin` role from `/auth/me`.
- **REQ-003**: Register flow shows a "check your email" confirmation — backend returns `{user_id}`, not tokens.
- **REQ-004**: Logout calls `POST /auth/logout` (server session revocation) before clearing in-memory state.
- **REQ-005**: On any 401, Axios interceptor attempts `POST /auth/refresh` once; if that also fails, redirect to `/login`.
- **REQ-006**: Dashboard displays username, email, `email_verified` status, roles, permissions, and active sessions count.
- **REQ-007**: Admin Dashboard lists users (paginated), lock/unlock, delete, and shows dashboard metrics.
- **SEC-001**: Tokens stored in React context (memory) only — never `localStorage` or `sessionStorage`.
- **SEC-002**: All API calls are same-origin (`/auth/*`, `/admin/*`) — no CORS needed in production.
- **CON-001**: Backend `/auth/register` returns `{user_id}` — frontend must not expect tokens after register.
- **CON-002**: Backend serves the built SPA: `main.py` mounts `./frontend/dist` as a `StaticFiles` mount at `/app` and serves `index.html` for all unmatched routes.
- **GUD-001**: Tailwind CSS v4 dark theme — background `#0f0f11`, accent `#7c6af7`, card `#1a1a1f`, border `#2a2a35`.
- **GUD-002**: All form schemas defined with Zod; `react-hook-form` + `@hookform/resolvers/zod` for form state.
- **PAT-001**: TanStack Router file-based routing under `frontend/src/routes/`.
- **PAT-002**: API layer in `frontend/src/lib/api.ts` — single Axios instance with request/response interceptors.
- **PAT-003**: Auth state in a React context (`AuthProvider`) — `user`, `login()`, `logout()`, `setUser()`.

## 2. Implementation Steps

> **Agent instructions**: After completing all tasks in a phase, stage with `git add -u` (plus explicit paths for new files) and commit. No `Co-authored-by:` trailers. Update checkboxes to `[x]` as each task is completed.

---

### Phase 1: Scaffold — Vite + React + TypeScript + Tailwind + TanStack

**Goal**: Get a working dev server with routing and styling configured so all later phases build on a stable foundation.

- [x] TASK-001: Run `npm create vite@latest frontend -- --template react-ts` from the repo root to scaffold the package.
- [x] TASK-002: In `frontend/`, install runtime deps: `npm i @tanstack/react-router @tanstack/react-query axios zod react-hook-form @hookform/resolvers`.
- [x] TASK-003: Install dev deps: `npm i -D @tanstack/router-plugin @tanstack/react-query-devtools tailwindcss @tailwindcss/vite`.
- [x] TASK-004: Configure `frontend/vite.config.ts` — add `@tailwindcss/vite` plugin, `@tanstack/router-plugin/vite` plugin, and a proxy for `/auth`, `/admin`, `/metrics` to `http://127.0.0.1:8000` (dev only).
- [x] TASK-005: Create `frontend/src/index.css` with Tailwind v4 import (`@import "tailwindcss"`) and CSS variables for the dark theme (`--color-bg: #0f0f11`, `--color-card: #1a1a1f`, `--color-border: #2a2a35`, `--color-accent: #7c6af7`).
- [x] TASK-006: Replace generated `frontend/src/main.tsx` — wrap app in `RouterProvider` (TanStack Router) and `QueryClientProvider` (TanStack Query).
- [x] TASK-007: Create `frontend/src/routeTree.gen.ts` placeholder and `frontend/src/routes/__root.tsx` as the root layout (renders `<Outlet />`).
- [x] TASK-008: Add `frontend/.gitignore` ignoring `node_modules/`, `dist/`, `.env`.
- [x] TASK-009: Update repo-root `.gitignore` to add `frontend/dist/` and `frontend/node_modules/`.

**Completion criteria**: `cd frontend && npm run dev` starts without errors; browser at `http://localhost:5173` shows a page without console errors.

**git commit**: `git add frontend/ && git commit -m "feat: scaffold React frontend with Vite, TanStack Router, Tailwind v4"`

---

### Phase 2: Auth layer — API client, AuthContext, token management

**Goal**: Establish the in-memory token store, Axios interceptor for transparent refresh, and the `AuthProvider` that all routes consume.

- [x] TASK-010: Create `frontend/src/lib/api.ts` — Axios instance with `baseURL: "/"`, `withCredentials: false`; attach `Authorization: Bearer <token>` from in-memory store on every request.
- [x] TASK-011: Add response interceptor in `api.ts`: on 401, attempt `POST /auth/refresh` with stored `refresh_token`; on success update in-memory tokens and retry original request; on failure navigate to `/login`.
- [x] TASK-012: Create `frontend/src/lib/tokens.ts` — module-level `let accessToken` and `let refreshToken` with `getTokens()`, `setTokens()`, `clearTokens()` exports (no `localStorage`).
- [x] TASK-013: Create `frontend/src/contexts/AuthContext.tsx` — `AuthProvider` fetches `/auth/me` on mount (if tokens exist) to populate `user`; exports `useAuth()` hook returning `{ user, login, logout, isLoading }`.
- [x] TASK-014: Implement `login(username, password)` in `AuthContext`: calls `POST /auth/login`, calls `setTokens()`, sets `user` from the response or a follow-up `/auth/me` call.
- [x] TASK-015: Implement `logout()` in `AuthContext`: calls `POST /auth/logout`, calls `clearTokens()`, sets `user` to `null`.
- [x] TASK-016: Create `frontend/src/components/ProtectedRoute.tsx` — renders children if `user !== null`, else `<Navigate to="/login" />`.
- [x] TASK-017: Create `frontend/src/components/AdminRoute.tsx` — renders children if `user.roles` includes `"admin"`, else `<Navigate to="/dashboard" />`.

**Completion criteria**: `AuthProvider` mounts without errors; `useAuth()` returns `{ user: null, isLoading: false }` on a fresh load; calling `login()` with valid credentials (via browser devtools) sets `user`.

**git commit**: `git add -u && git add frontend/src/lib/ frontend/src/contexts/ frontend/src/components/ && git commit -m "feat: add auth context, in-memory token store, and Axios interceptor"`

---

### Phase 3: Auth pages — Login, Register, Forgot/Reset Password, Verify Email

**Goal**: All unauthenticated flows with Zod-validated forms and correct post-action routing.

- [x] TASK-018: Create `frontend/src/routes/login.tsx` — form with `username` + `password` fields; Zod schema: both required, non-empty; on success calls `AuthContext.login()` and navigates to `/dashboard`; on MFA required (`mfa_required: true`) navigates to `/login/mfa`.
- [x] TASK-019: Create `frontend/src/routes/login.mfa.tsx` — form with `mfa_session_token` (hidden, from route state) + `code` + `is_backup_code` toggle; calls `POST /auth/login/mfa`; on success sets tokens and navigates to `/dashboard`.
- [x] TASK-020: Create `frontend/src/routes/register.tsx` — form with `username`, `email`, `password`; Zod schema mirrors backend rules (min 3 chars username, email format, min 8 chars password with uppercase + digit); calls `POST /auth/register`; on success navigates to `/register/success` (no tokens expected).
- [x] TASK-021: Create `frontend/src/routes/register.success.tsx` — static "Check your email" confirmation card with link back to `/login`.
- [x] TASK-022: Create `frontend/src/routes/verify-email.tsx` — reads `token` from URL search param; calls `POST /auth/verify-email` with `{ token }`; shows success or error message.
- [x] TASK-023: Create `frontend/src/routes/forgot-password.tsx` — form with `email`; calls `POST /auth/forgot-password`; always shows neutral "If that email exists…" message after submit.
- [x] TASK-024: Create `frontend/src/routes/reset-password.tsx` — reads `token` from URL search param; form with `new_password` (Zod: min 8, uppercase, digit); calls `POST /auth/reset-password`; on success navigates to `/login` with a success flash.
- [x] TASK-025: Create `frontend/src/components/FormError.tsx` — reusable error banner component (matches existing `.error` CSS: dark red background, red border, light red text).

**Completion criteria**: Navigating to `/login`, `/register`, `/forgot-password`, `/reset-password?token=x`, `/verify-email?token=x` all render without errors; submitting an empty login form shows Zod validation errors inline without a network call.

**git commit**: `git add -u && git add frontend/src/routes/ frontend/src/components/FormError.tsx && git commit -m "feat: add login, register, password reset, and email verification pages"`

---

### Phase 4: Dashboard

**Goal**: Authenticated user home screen showing profile, roles/permissions, email verification status, and active sessions.

- [x] TASK-026: Create `frontend/src/routes/dashboard.tsx` — wrap with `ProtectedRoute`; fetch `/auth/me` via TanStack Query (`useQuery`); display username, email, `email_verified` badge, roles list, permissions list.
- [x] TASK-027: Add active sessions tile to dashboard — fetch `GET /auth/sessions`; display count and list of sessions (device, browser, OS, last active); include "Revoke" button per session calling `DELETE /auth/sessions/{id}`.
- [x] TASK-028: Add MFA status tile — if `/auth/me` (or a separate `/auth/mfa/status`) shows MFA enabled, show "MFA active" badge; otherwise show "Enable MFA" button linking to `/dashboard/mfa`.
- [x] TASK-029: Create `frontend/src/routes/dashboard.mfa.tsx` — calls `POST /auth/mfa/setup`; displays QR URI in an `<img src="...">` (use `qrcode` npm package to render client-side) + secret + backup codes; has a "Verify" form calling `POST /auth/mfa/verify`.
- [x] TASK-030: Create `frontend/src/components/Topbar.tsx` — FastAuth logo + "Sign out" button calling `AuthContext.logout()`; used on all authenticated pages.
- [x] TASK-031: Add "Change password" section to dashboard — form with `current_password` + `new_password`; Zod validation (same strength rules); calls `POST /auth/change-password`.

**Completion criteria**: Logged-in user sees their username, email, verified status, roles, and sessions on `/dashboard`; clicking "Sign out" calls `POST /auth/logout` and redirects to `/login`.

**git commit**: `git add -u && git add frontend/src/routes/dashboard* frontend/src/components/Topbar.tsx && git commit -m "feat: add user dashboard with sessions, MFA, and change password"`

---

### Phase 5: Admin Dashboard

**Goal**: Admin-only area for user management and system metrics.

- [x] TASK-032: Create `frontend/src/routes/admin.tsx` — wrap with `AdminRoute`; fetch `GET /admin/dashboard` via TanStack Query; display 4 metric tiles: total users, active sessions, MFA-enabled users, failed logins 24h.
- [x] TASK-033: Add paginated user table to admin page — fetch `GET /admin/users?page=N&limit=50&search=...`; columns: username, email, created, locked status; row actions: Lock, Unlock, Delete (with confirm dialog).
- [x] TASK-034: Add OAuth client management section — list `GET /admin/oauth/clients`; "Create client" form with `name`, `redirect_uris`, `scopes`, `is_confidential`; revoke button.
- [x] TASK-035: Create `frontend/src/components/ConfirmDialog.tsx` — reusable modal for destructive actions (Delete, Bulk delete).

**Completion criteria**: Navigating to `/admin` as a non-admin redirects to `/dashboard`; as an admin, metrics tiles load and user table renders with working lock/unlock/delete actions.

**git commit**: `git add -u && git add frontend/src/routes/admin* frontend/src/components/ConfirmDialog.tsx && git commit -m "feat: add admin dashboard with user management and OAuth clients"`

---

### Phase 6: FastAPI integration — serve SPA in production

**Goal**: Wire the built frontend into the FastAPI app so a single `uvicorn main:app` serves everything.

- [x] TASK-036: In `main.py`, add `app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="frontend-assets")` after all API routers — only when `frontend/dist` exists (guard with `Path("frontend/dist").exists()`).
- [x] TASK-037: Update `app/web/router.py` to serve `frontend/dist/index.html` for `/`, `/login`, `/register`, `/dashboard`, `/admin`, `/forgot-password`, `/reset-password`, `/verify-email` when `frontend/dist/index.html` exists; fall back to Jinja2 templates otherwise.
- [x] TASK-038: Add `frontend/` build step to `pyproject.toml` `[tool.hatch.build]` or document in `README` — `cd frontend && npm ci && npm run build`.
- [x] TASK-039: Update `.github/workflows/unit-test.yml` to run `npm ci && npm run build` in `frontend/` before the Python tests so the CI also validates the frontend build.
- [x] TASK-040: Jinja2 templates retained as fallback (web router serves them when SPA build is absent); deletion deferred until production deployment confirms SPA-only path.

**Completion criteria**: `cd frontend && npm run build` exits 0; `uvicorn main:app` at `http://localhost:8000/login` serves the React SPA; API calls to `/auth/login` work from the SPA without CORS errors.

**git commit**: `git add -u && git commit -m "feat: serve built React SPA from FastAPI; remove Jinja2 templates"`

---

## 3. Alternatives Considered

- **ALT-001**: `httpOnly` cookie token storage — ideal security posture, but requires a backend `POST /auth/login/cookie` endpoint that sets `Set-Cookie` headers; deferred to avoid backend changes in this plan. In-memory storage is the next-best option (not persistent across hard refresh — trade-off accepted).
- **ALT-002**: Next.js instead of Vite + TanStack Router — rejected because the backend is FastAPI serving a static SPA; Next.js SSR adds operational complexity with no benefit here.
- **ALT-003**: Zustand for auth state instead of React Context — rejected; the auth state shape is simple enough that Context + TanStack Query covers it without an extra dependency.

## 4. Dependencies

- **DEP-001**: Node.js ≥ 20 and npm ≥ 10 on the dev machine and CI runner.
- **DEP-002**: FastAPI backend running at `http://127.0.0.1:8000` for Vite proxy during development.
- **DEP-003**: `qrcode` npm package for client-side QR code rendering in MFA setup.

## 5. Affected Files

- **FILE-001**: `frontend/` — new package (all new files)
- **FILE-002**: `main.py` — mount `StaticFiles` for `frontend/dist`
- **FILE-003**: `app/web/router.py` — serve SPA `index.html` for all frontend routes
- **FILE-004**: `templates/` — deleted (all 5 Jinja2 templates)
- **FILE-005**: `.gitignore` — add `frontend/dist/`, `frontend/node_modules/`
- **FILE-006**: `.github/workflows/unit-test.yml` — add frontend build step

## 6. Testing

- [ ] TEST-001: Manual — submit empty login form; verify inline Zod errors appear and no network request is made.
- [ ] TEST-002: Manual — register with a weak password (no uppercase); verify error message "password must contain at least one uppercase letter".
- [ ] TEST-003: Manual — log in, copy access token from devtools memory (breakpoint in `setTokens`), close tab, reopen; verify user is logged out (token gone from memory).
- [ ] TEST-004: Manual — log in, let access token expire (or manually call `clearTokens()` in devtools), navigate to `/dashboard`; verify interceptor calls `/auth/refresh` and reloads the page without redirecting to login.
- [ ] TEST-005: Manual — log in as non-admin, navigate to `/admin`; verify redirect to `/dashboard`.
- [ ] TEST-006: Manual — log in as admin, navigate to `/admin`; verify metrics tiles and user table load.
- [x] TEST-007: `cd frontend && npm run build` — exits 0 with no TypeScript errors (verified: `tsc -b` passes, vite build succeeds).

## 7. Risks & Assumptions

- **RISK-001**: In-memory token storage is lost on page refresh, requiring re-login — mitigation: implement a silent refresh via a short-lived `httpOnly` refresh cookie in a follow-up plan (ALT-001).
- **RISK-002**: TanStack Router file-based routing requires the Vite plugin; if plugin version mismatches with router version, route generation will fail — mitigation: pin compatible versions together in `package.json`.
- **ASSUMPTION-001**: The FastAPI backend already has `POST /auth/refresh` returning `{access_token, refresh_token}` — confirmed from existing `app/auth/router.py`.
- **ASSUMPTION-002**: `GET /auth/sessions` returns a list of active sessions — confirmed from `app/auth/sessions/router.py`.
- **ASSUMPTION-003**: MFA setup endpoint is `POST /auth/mfa/setup` returning `{secret, qr_code_uri, backup_codes}` — confirmed from `app/auth/mfa/router.py`.

## 8. Architecture Diagram

```mermaid
graph TD
    Browser -->|/login /dashboard etc| FastAPI
    FastAPI -->|frontend/dist/index.html| Browser
    Browser -->|POST /auth/login| FastAPI
    FastAPI -->|{access_token, refresh_token}| Browser
    Browser -->|in-memory tokens| AxiosInterceptor
    AxiosInterceptor -->|Bearer token| FastAPI
    AxiosInterceptor -->|POST /auth/refresh on 401| FastAPI

    subgraph React SPA
        TanStackRouter --> AuthPages
        TanStackRouter --> ProtectedRoutes
        TanStackRouter --> AdminRoutes
        AuthContext --> AxiosInterceptor
        TanStackQuery --> API_Calls
    end
```

## 9. Related Specs & Further Reading

- `docs/ddd-sqlalchemy-migration/PLAN.md` — backend DDD structure the API layer consumes
- `app/auth/router.py` — login, register, refresh, me, logout endpoints
- `app/auth/sessions/router.py` — sessions list and revoke endpoints
- `app/auth/mfa/router.py` — MFA setup, verify, backup codes endpoints
- `app/admin/router.py` — admin dashboard, user management, OAuth clients
