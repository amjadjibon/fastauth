# Admin API Reference

All admin endpoints require the `admin` role. Requests must include `Authorization: Bearer <access_token>`.

## User Management

### List Users: `GET /admin/users`

**Query params**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `limit` | int | 50 | Results per page (max 200) |
| `search` | string | — | Filter by username or email |
| `status` | string | — | `active`, `locked`, `all` |

**Response** `200 OK`
```json
{
  "total": 1234,
  "page": 1,
  "limit": 50,
  "users": [
    {
      "id": "uuid",
      "username": "johndoe",
      "email": "john@example.com",
      "is_active": true,
      "is_locked": false,
      "mfa_enabled": true,
      "created_at": "2026-01-01T00:00:00Z",
      "last_login_at": "2026-06-13T10:00:00Z"
    }
  ]
}
```

### Get User: `GET /admin/users/{user_id}`

Returns full user detail including roles, permissions, active sessions, and recent audit events.

### Update User: `PATCH /admin/users/{user_id}`

**Request body** (all fields optional)
```json
{
  "email": "newemail@example.com",
  "is_active": true
}
```

### Delete User: `DELETE /admin/users/{user_id}`

Permanently deletes the user and all associated data. Returns `204 No Content`.

### Lock User: `POST /admin/users/{user_id}/lock`

Blocks the user from logging in without deleting the account. Returns `200 OK`.

### Unlock User: `POST /admin/users/{user_id}/unlock`

Re-enables a locked account. Returns `200 OK`.

### Force Password Reset: `POST /admin/users/{user_id}/force-password-reset`

Invalidates the user's current password and sends a reset email. Returns `200 OK`.

---

## Bulk Operations

### Bulk Lock: `POST /admin/users/bulk-lock`

```json
{ "user_ids": ["uuid1", "uuid2"] }
```

### Bulk Delete: `POST /admin/users/bulk-delete`

```json
{ "user_ids": ["uuid1", "uuid2"] }
```

---

## Dashboard Metrics: `GET /admin/dashboard`

**Response** `200 OK`
```json
{
  "total_users": 5000,
  "active_sessions": 312,
  "mfa_enabled_users": 1840,
  "failed_login_attempts_24h": 23
}
```

---

## Audit Logs

### List Audit Logs: `GET /auth/audit/logs`

**Query params**: `user_id`, `event_type`, `from_date`, `to_date`, `page`, `limit`

**Response** `200 OK`
```json
{
  "total": 8921,
  "logs": [
    {
      "id": "uuid",
      "event_type": "login_success",
      "user_id": "uuid",
      "ip_address": "192.168.x.x",
      "outcome": "success",
      "created_at": "2026-06-13T10:00:00Z"
    }
  ]
}
```

### Export Audit Logs: `GET /auth/audit/logs/export`

**Query params**: `format` (`csv` or `json`), same filters as above.

Returns file download with `Content-Disposition: attachment`.

---

## RBAC

### List Roles: `GET /admin/roles`

### Create Role: `POST /admin/roles`

```json
{ "name": "editor", "description": "Can edit content" }
```

### Assign Role to User: `POST /admin/roles/{role_id}/assign`

```json
{ "user_id": "uuid" }
```

### List Permissions: `GET /admin/permissions`

### Create Permission: `POST /admin/permissions`

```json
{ "resource": "posts", "action": "write" }
```

### Assign Permission to Role: `POST /admin/roles/{role_id}/permissions`

```json
{ "permission_id": "uuid" }
```
