---
date: 2026-06-14
branch: react-frontend
reviewer: Claude
verdict: Request Changes
---

# Code Review: react-frontend

## Verdict

**Request Changes** — one High bug breaks the MFA login flow entirely; one Medium means MFA status is always shown as disabled; both are straightforward to fix.

## Summary

Reviewed 41 changed files adding a full React 19 / TanStack Router SPA replacing the Jinja2 templates. The architecture is sound — in-memory token storage, transparent Axios refresh interceptor, Zod-validated forms, protected and admin routes, and a clean FastAPI fallback. Two functional bugs need fixing before merge: MFA session token routing is broken because TanStack Router doesn't support `state` in `navigate()` options (the `as never` cast silently swallows the TypeScript error), and the MFA status tile always shows "disabled" because the `GET /auth/mfa/status` endpoint called by the dashboard does not exist on the backend.

---

## Findings

### [HIGH-001] MFA login flow broken — session token never reaches `/login/mfa` *(High)*

**File**: `frontend/src/routes/login.tsx:37-39`, `frontend/src/routes/login.mfa.tsx:30`

**Category**: Correctness

**Issue**: `login.tsx` navigates to `/login/mfa` passing `state: { mfaSessionToken: ... }`. TanStack Router v1 does not recognise `state` as a navigate option; the `as never` cast on line 39 suppresses the resulting TypeScript error rather than fixing it. As a result the token is never stored anywhere TanStack Router can retrieve it. In `login.mfa.tsx` line 30, `history.state` is read directly from the browser's history object, which only contains TanStack Router's own internal keys (`__TSR_*`). `state.mfaSessionToken` is always `undefined`, so every MFA submission sends `mfa_session_token: undefined` and the backend rejects it with 400/422.

**Fix**: Pass the token as a URL search param instead — the correct, type-safe TanStack Router idiom:

```tsx
// login.tsx — define search validator on the mfa route first, then:
navigate({ to: '/login/mfa', search: { mfaToken: result.mfa_session_token ?? '' } })

// login.mfa.tsx — add validateSearch and read from it:
export const Route = createFileRoute('/login/mfa')({
  validateSearch: (s: Record<string, unknown>) => ({ mfaToken: (s.mfaToken as string) ?? '' }),
  component: MfaPage,
})

function MfaPage() {
  const { mfaToken } = Route.useSearch()
  // replace: state.mfaSessionToken → mfaToken
}
```

Remove the `as never` cast from `login.tsx`. The TypeScript error it was hiding will resolve once `search` is used correctly.

---

### [MED-001] `GET /auth/mfa/status` does not exist — MFA tile always shows disabled *(Medium)*

**File**: `frontend/src/routes/dashboard.tsx:100-102`

**Category**: Correctness

**Issue**: The dashboard queries `GET /auth/mfa/status` which is not defined in `app/auth/mfa/router.py`. The `.catch(() => ({ enabled: false }))` swallows the 404 silently, so `mfaStatus.enabled` is always `false` regardless of whether the user has MFA set up. The "Enable MFA" button shows even for users with MFA active.

**Fix** (two options — pick one):

Option A — add a thin backend endpoint:
```python
# app/auth/mfa/router.py
@router.get("/status")
async def mfa_status(current_user: CurrentUser, session: SessionDep):
    enabled = await mfa_service.is_mfa_enabled(session, current_user.id)
    return {"enabled": enabled}
```

Option B — derive from `/auth/me` (no backend change needed). The `/me` endpoint already queries MFA state internally for the login flow; add `mfa_enabled: bool` to `UserResponse` and `User` interface, and read it from `useAuth().user` instead of making a separate fetch.

---

### [MED-002] MFA setup failure leaves a blank card *(Medium)*

**File**: `frontend/src/routes/dashboard.mfa.tsx:48`

**Category**: Correctness

**Issue**: When `POST /auth/mfa/setup` fails, the catch sets `step = 'setup'` but leaves `setup` state as `null`. The render condition is `step === 'setup' && setup && (...)`, so nothing renders — the user sees a blank card with no error message and no way to retry.

**Fix**:

```tsx
.catch((err: unknown) => {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ?? 'Failed to set up MFA. Please try again.'
  setServerError(detail)
  setStep('error')  // add an 'error' step
})
```

Add a `step === 'error'` branch that renders the error and a "Try again" button.

---

### [MED-003] Admin user search fires a query on every keystroke *(Medium)*

**File**: `frontend/src/routes/admin.tsx:80-89`

**Category**: Performance

**Issue**: Updating `search` state immediately changes the query key `['admin-users', page, search]`, triggering a new API call on every character typed. For a large user base this creates unnecessary backend load and a flickering table on every keystroke.

**Fix**: Debounce the search value before using it in the query key:

```tsx
import { useDeferredValue } from 'react'
// or a small useDebouncedValue hook:
const debouncedSearch = useDeferredValue(search) // built-in React 18 primitive
// ...
queryKey: ['admin-users', page, debouncedSearch],
queryFn: () => api.get(`/admin/users?page=${page}&limit=20&search=${encodeURIComponent(debouncedSearch)}`),
```

---

### [LOW-001] `_SPA_ROUTES` is defined but never used *(Low)*

**File**: `app/web/router.py:7-8`

**Category**: Simplicity

**Issue**: `_SPA_ROUTES = [...]` is assigned but never referenced anywhere in the file. Dead code.

**Fix**: Delete lines 7-8.

---

### [LOW-002] Extra parentheses on first route registration *(Low)*

**File**: `app/web/router.py:31`

**Category**: Simplicity

**Issue**: `router.get("/")((_spa_or_template("login.html")))` has a redundant outer pair of parentheses, inconsistent with all other registrations on the following lines.

**Fix**: `router.get("/")(_spa_or_template("login.html"))`

---

### [LOW-003] `Path("frontend/dist")` is CWD-relative in `main.py` *(Low)*

**File**: `main.py:136`

**Category**: Correctness

**Issue**: `Path("frontend/dist")` resolves relative to the process working directory. It works when `uvicorn` is started from the repo root, but silently skips the static mount if started from elsewhere, producing no error and no assets.

**Fix**: Use an absolute path anchored to `main.py`:

```python
_frontend_dist = Path(__file__).resolve().parent / "frontend" / "dist"
```

---

## What's Good

- **In-memory token storage is correctly implemented** — `tokens.ts` uses module-level variables with no `localStorage` or `sessionStorage` touch, and the comment explains the intentional trade-off clearly.
- **Refresh interceptor handles concurrent 401s correctly** — the `refreshing` promise variable deduplicates parallel refresh attempts, preventing multiple simultaneous refresh calls from racing. This is easy to get wrong and was done right.
- **Zod schemas mirror backend validation rules** — `register.tsx` enforces the same username character set, min length, email format, and password strength constraints as the Python backend, so server-side errors are rare rather than the first line of defence.

---

## Pre-Merge Checklist

**Always:**
- [ ] All Critical and High findings resolved
- [ ] No secrets or credentials in committed files
- [ ] `.gitignore` covers new artifact/config types introduced
- [ ] Tests cover the changed behaviour and at least one unhappy path
- [ ] All async calls awaited or errors handled
- [ ] Resources (files, connections, streams) closed in all code paths

**If this touches auth, sessions, or user data:**
- [x] Tokens in memory (not `localStorage`) ✓
- [ ] CSRF protection on state-changing endpoints — out of scope for this PR (backend concern), but worth a follow-up ticket
- [x] Rate limiting on login/signup endpoints — already enforced on the backend ✓
- [x] No sensitive data in error responses or logs ✓
