---
goal: Fix all findings from the react-frontend code review
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: Amjad Hossain
status: 'In progress'
tags: [bug]
---

# Fix React Frontend Review Findings

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

The code review of PR #9 (`react-frontend`) identified one high-severity bug that breaks the MFA login flow entirely, two medium bugs (missing backend endpoint, blank error card on MFA setup failure, unbounded search requests), and three low-priority cleanups. This plan fixes all findings in severity order so the highest-impact issue ships first.

## 1. Requirements & Constraints

- **REQ-001**: MFA login must succeed end-to-end — the session token must reach `/login/mfa` from `/login` and be sent to `POST /auth/login/mfa`.
- **REQ-002**: The MFA status tile on the dashboard must reflect the user's actual MFA state.
- **REQ-003**: MFA setup failure must show an error message and a retry button — no blank cards.
- **REQ-004**: Admin user search must debounce API calls so a single keystroke doesn't fire a backend query.
- **CON-001**: MFA session token is sensitive — must not be stored in localStorage or a React ref that survives remount; URL search param is acceptable because the token is short-lived (TTL enforced by backend) and the route redirects immediately after use.
- **CON-002**: Backend `GET /auth/mfa/status` must be added before the frontend query can work; frontend and backend changes land in the same phase.
- **GUD-001**: Use TanStack Router's `validateSearch` + `Route.useSearch()` for typed search params — never read `window.history.state` directly.

## 2. Implementation Steps

> **Agent instructions**: After completing all tasks in a phase, stage with `git add -u` (plus explicit paths for new files) and commit. No `Co-authored-by:` trailers. Update checkboxes to `[x]` as each task is completed.

---

### Phase 1: Fix MFA login token routing (HIGH-001)

**Goal**: Pass `mfa_session_token` from `/login` to `/login/mfa` via typed URL search params so the MFA submission can include it.

- [ ] TASK-001: In `frontend/src/routes/login.mfa.tsx`, add `validateSearch: (s: Record<string, unknown>) => ({ mfaToken: (s.mfaToken as string) ?? '' })` to the `createFileRoute('/login/mfa')` options, and replace the `history.state` read with `const { mfaToken } = Route.useSearch()`. Update all references from `state.mfaSessionToken` → `mfaToken`.
- [ ] TASK-002: In `frontend/src/routes/login.tsx`, replace the `navigate({ to: '/login/mfa', state: { mfaSessionToken: ... } } as never)` call with `navigate({ to: '/login/mfa', search: { mfaToken: result.mfa_session_token ?? '' } })` — remove the `as never` cast entirely.
- [ ] TASK-003: Rebuild the frontend (`cd frontend && npm run build`) to confirm no TypeScript errors remain after removing the `as never` cast.

**Completion criteria**: `npm run build` exits 0 with no TypeScript errors; the `as never` cast is gone from `login.tsx`.

**git commit**: `git add -u && git commit -m "fix: pass MFA session token via search param, not history.state"` — no `Co-authored-by:` trailer

---

### Phase 2: Add backend MFA status endpoint + fix frontend tile (MED-001)

**Goal**: Dashboard MFA tile must reflect actual MFA state. The backend `GET /auth/mfa/status` endpoint is missing; the frontend silently catches the 404 and always shows "disabled".

- [ ] TASK-004: In `app/auth/mfa/router.py`, add a new `GET /status` endpoint after the existing routes:
  ```python
  @router.get("/status")
  async def mfa_status(current_user: CurrentUser, session: SessionDep):
      enabled = await mfa_service.is_mfa_enabled(session, current_user.id)
      return {"enabled": enabled}
  ```
- [ ] TASK-005: In `frontend/src/routes/dashboard.tsx`, remove the `.catch(() => ({ enabled: false }))` from the `mfa-status` query so a backend error is visible rather than silently swallowed.

**Completion criteria**: `GET /auth/mfa/status` returns `{"enabled": true}` for a user with MFA set up and `{"enabled": false}` otherwise (verify with `curl -H "Authorization: Bearer <token>" http://localhost:8000/auth/mfa/status`).

**git commit**: `git add -u && git commit -m "fix: add GET /auth/mfa/status endpoint; surface error in dashboard tile"` — no `Co-authored-by:` trailer

---

### Phase 3: Fix MFA setup blank card on failure (MED-002)

**Goal**: When `POST /auth/mfa/setup` fails, the user must see an error message and a "Try again" button instead of a blank card.

- [ ] TASK-006: In `frontend/src/routes/dashboard.mfa.tsx`, add `'error'` to the step type union: `useState<'loading' | 'setup' | 'success' | 'error'>('loading')`.
- [ ] TASK-007: In the same file, replace `.catch(() => setStep('setup'))` with:
  ```tsx
  .catch((err: unknown) => {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      ?? 'Failed to set up MFA. Please try again.'
    setServerError(detail)
    setStep('error')
  })
  ```
- [ ] TASK-008: Add an `{step === 'error' && ...}` branch in the JSX that renders `<FormError message={serverError} />` and a "Try again" button that resets `didSetup.current = false` and calls `setStep('loading')` then re-triggers the setup effect.

**Completion criteria**: Simulating a network failure on the setup POST (e.g. backend down) renders an error message and a "Try again" button — not a blank card.

**git commit**: `git add -u && git commit -m "fix: show error and retry button when MFA setup POST fails"` — no `Co-authored-by:` trailer

---

### Phase 4: Debounce admin user search (MED-003)

**Goal**: Typing in the admin search box should not fire one API call per character; debounce so the query only runs when the user pauses.

- [ ] TASK-009: In `frontend/src/routes/admin.tsx`, import `useDeferredValue` from `'react'` and derive `const deferredSearch = useDeferredValue(search)` from the existing `search` state.
- [ ] TASK-010: Replace all three references to `search` inside the `useQuery` block (query key array and the URL string) with `deferredSearch`, so rapid keystrokes update the input immediately but only commit a new fetch when React schedules it.

**Completion criteria**: Typing rapidly in the search box triggers at most one in-flight request at a time (verify in browser Network tab — no burst of sequential requests on each keystroke).

**git commit**: `git add -u && git commit -m "fix: debounce admin user search with useDeferredValue"` — no `Co-authored-by:` trailer

---

### Phase 5: Low-severity cleanups (LOW-001, LOW-002, LOW-003)

**Goal**: Remove dead code and make path resolution robust.

- [ ] TASK-011: In `app/web/router.py`, delete the unused `_SPA_ROUTES = [...]` assignment (lines 7–8).
- [ ] TASK-012: In `app/web/router.py`, remove the extra outer parentheses from `router.get("/")((_spa_or_template("login.html")))` → `router.get("/")(_spa_or_template("login.html"))`.
- [ ] TASK-013: In `main.py`, change `_frontend_dist = Path("frontend/dist")` to `_frontend_dist = Path(__file__).resolve().parent / "frontend" / "dist"` so the path resolves correctly regardless of the working directory when uvicorn starts.

**Completion criteria**: `grep "_SPA_ROUTES" app/web/router.py` returns nothing; `grep 'Path("frontend/dist")' main.py` returns nothing.

**git commit**: `git add -u && git commit -m "chore: remove dead code and fix CWD-relative path in main.py"` — no `Co-authored-by:` trailer

---

## 5. Affected Files

- **FILE-001**: `frontend/src/routes/login.tsx` — replace `state`/`as never` with typed search param
- **FILE-002**: `frontend/src/routes/login.mfa.tsx` — add `validateSearch`, read `mfaToken` from search
- **FILE-003**: `frontend/src/routes/dashboard.tsx` — remove silent catch on mfa-status query
- **FILE-004**: `frontend/src/routes/dashboard.mfa.tsx` — add error step + retry
- **FILE-005**: `frontend/src/routes/admin.tsx` — debounce search with `useDeferredValue`
- **FILE-006**: `app/auth/mfa/router.py` — add `GET /status` endpoint
- **FILE-007**: `app/web/router.py` — delete `_SPA_ROUTES`, fix extra parens
- **FILE-008**: `main.py` — fix CWD-relative `Path("frontend/dist")`

## 6. Testing

- [ ] TEST-001: Manual — log in with MFA-enabled account; verify the `/login/mfa` page receives `mfaToken` in the URL search params and submits it to the backend successfully.
- [ ] TEST-002: Manual — `curl -H "Authorization: Bearer <token>" http://localhost:8000/auth/mfa/status` returns `{"enabled": true}` after MFA setup.
- [ ] TEST-003: Manual — navigate to `/dashboard/mfa` with the backend down; verify an error message and "Try again" button appear instead of a blank card.
- [ ] TEST-004: Manual — type rapidly in the admin search box while watching the Network tab; verify no burst of sequential requests fires on every keystroke.
- [ ] TEST-005: Run `cd frontend && npm run build` — exits 0, no TypeScript errors, no `as never` cast remaining.

## 9. Related Specs & Further Reading

- `docs/react-frontend/REVIEW.md` — source of all findings addressed by this plan
- `docs/react-frontend/PLAN.md` — original frontend implementation plan
