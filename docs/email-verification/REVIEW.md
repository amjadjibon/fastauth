---
iteration: 3
verdict: Approve
---

# Code Review — Email Verification (Iteration 3)

## Verdict: Approve

All High and Medium findings from iteration 2 are resolved. One Low maintenance concern (LOW-006) and three Info items remain open; none are blockers.

---

## Previously Fixed (Iteration 2)

| ID | Finding | Status |
|----|---------|--------|
| HIGH-004 | Raw reset token written to DEBUG log in `forgot_password` | **Fixed** — line 351 now logs only `user_id`. |
| MED-005 | No test for resend-invalidation path | **Fixed** — `test_resend_invalidates_old_token` registers, resends, asserts old token → 400 and new token → 200. |
| MED-006 | Non-atomic social user creation | **Fixed** — `auto_create_user_on_social_login` uses `create_no_commit`; user row and social account row committed in a single `await session.commit()`. |
| LOW-007 | Duplicate email in register → HTTP 500 | **Fixed** — explicit `store.get_by_email` pre-check raises 409 before the INSERT. |
| LOW-002 | `ResetPasswordRequest.token` missing `max_length` | **Fixed** — `max_length=128` added. |

---

## Remaining Findings

### Critical / High / Medium

None.

---

### Low

**LOW-006 (open, unchanged): Email dispatch inconsistency between `register` and `resend_verification`**

`_issue_verification_token(commit=True)` sends the email internally after its own commit (used by `resend_verification`). `register` uses `commit=False` and sends the email itself after its own commit. Both are correct today, but the split behaviour means a future refactor of `_issue_verification_token` could accidentally re-introduce email inside the transaction. Not a merge blocker; acceptable to track as a follow-up cleanup.

---

### Info

**INFO-005 (open): `with_for_update()` is a no-op on SQLite in the test suite**

Tests confirm the token is consumed; the concurrent double-submit path is not exercised. No regression — PostgreSQL will lock correctly in production.

**INFO-006 (open): `RegisterResponse` has no `email_verification_required` field**

API clients cannot distinguish "registration succeeded, verification pending" from "registration succeeded, no verification needed" without inspecting the settings. Deferred.

**INFO-007 (open): No scheduled cleanup for `email_verification_tokens`**

Expired rows accumulate indefinitely. Acceptable to defer.

---

## What's Good

- All security findings across three iterations resolved: no raw token in any log path, single-transaction registration, TOCTOU-safe token consumption, social login atomicity, and the email-verification enforcement gate.
- Test suite now covers 8 scenarios including the resend-invalidation contract; mock patching approach is clean and portable.
- `store.get_by_email` pre-check on register converts a 500 IntegrityError into a proper 409 with no observable timing difference from the username check.

---

## Pre-Merge Checklist

**Always:**
- [x] All Critical and High findings resolved
- [x] No secrets or credentials in committed files
- [x] `.gitignore` covers new artifact/config types introduced
- [x] Tests cover the changed behaviour and at least one unhappy path
- [x] All async calls awaited or errors handled
- [x] Resources (files, connections, streams) closed in all code paths

**Auth, sessions, and user data:**
- [x] Tokens in `httpOnly` cookies, not `localStorage`
- [x] Rate limiting on login, signup, and verification endpoints
- [x] No sensitive data in error responses or logs
