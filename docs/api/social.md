# Social Login API Reference

FastAuth supports OAuth2-based social login via Google, GitHub, and GitLab.

## Supported Providers

| Provider | Environment variables required |
|----------|-------------------------------|
| `google` | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| `github` | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` |
| `gitlab` | `GITLAB_CLIENT_ID`, `GITLAB_CLIENT_SECRET` |

---

## Social Login Flow

### Step 1 — Get Authorization URL: `GET /auth/social/{provider}/authorize`

**Path params**: `provider` — one of `google`, `github`, `gitlab`

Redirects the browser to the provider's authorization page.

```
GET /auth/social/google/authorize
→ 302 https://accounts.google.com/o/oauth2/auth?client_id=...&redirect_uri=...&scope=...
```

### Step 2 — Handle Callback: `GET /auth/social/{provider}/callback`

The provider redirects here after user consent.

**Query params**: `code`, `state`

**Response** `200 OK`
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "Bearer",
  "is_new_user": true
}
```

On first login, an account is automatically created from the provider's profile data.

---

## Account Linking

### Link Social Account: `POST /auth/social/link`

Requires `Authorization: Bearer <access_token>`.

Links an additional social provider to an existing account.

**Request body**
```json
{
  "provider": "github",
  "code": "oauth-code-from-provider",
  "redirect_uri": "https://myapp.example.com/callback"
}
```

**Response** `200 OK`
```json
{
  "provider": "github",
  "provider_user_id": "1234567",
  "linked_at": "2026-06-13T10:00:00Z"
}
```

### List Linked Accounts: `GET /auth/social/linked`

Requires `Authorization: Bearer <access_token>`.

**Response** `200 OK`
```json
[
  {
    "provider": "google",
    "provider_user_id": "108...",
    "linked_at": "2026-06-01T09:00:00Z"
  }
]
```

### Unlink Account: `DELETE /auth/social/unlink/{provider}`

Requires `Authorization: Bearer <access_token>`.

Cannot unlink if it's the only login method and no password is set.

**Response** `204 No Content`

---

## Notes

- State parameter is used for CSRF protection; validate it in your callback handler
- GitHub users without a public email require the `user:email` scope (included by default)
- GitLab self-hosted: set `GITLAB_BASE_URL` to override `https://gitlab.com`
