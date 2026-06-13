---
goal: Production-grade authentication system with OAuth2, MFA, SSO, and session management
version: 1.0
date_created: 2026-06-13
last_updated: 2026-06-13
owner: fastauth-team
status: 'In progress'
tags: [feature, architecture, security]
---

# Production-Grade Authentication Implementation Plan

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

This plan transforms the current FastAuth basic JWT implementation into a production-grade authentication system comparable to Keycloak, Authentik, or Supabase Auth. The implementation adds OAuth2/OIDC support, multi-factor authentication (MFA), single sign-on (SSO), session management, security hardening, and comprehensive observability.

## 1. Requirements & Constraints

- **REQ-001**: Support OAuth2 authorization code flow with PKCE for web/mobile clients
- **REQ-002**: Support OpenID Connect (OIDC) discovery endpoints
- **REQ-003**: Implement TOTP-based multi-factor authentication (MFA)
- **REQ-004**: Implement session management with revocation capabilities
- **REQ-005**: Support social login providers (Google, GitHub, GitLab)
- **REQ-006**: Implement role-based access control (RBAC) with permissions
- **SEC-001**: All secrets must be encrypted at rest using AWS KMS or equivalent
- **SEC-002**: Implement rate limiting per IP, per user, and per endpoint
- **SEC-003**: Support brute-force protection with account lockout
- **SEC-004**: Implement security audit logging for all auth events
- **CON-001**: Must maintain backward compatibility with existing JWT endpoints
- **CON-002**: Must support both SQLite (dev) and PostgreSQL (production)
- **GUD-001**: Follow OWASP authentication security recommendations
- **PAT-001**: Use repository pattern for data access
- **PAT-002**: Use dependency injection for services

## 2. Implementation Steps

> **Agent instructions**: Before each phase, create a new branch. After completing all tasks in a phase, commit with descriptive message. Update checkboxes to `[x]` as each task is completed.

### Phase 1: Database Schema & Migrations

**Goal**: Create comprehensive database schema supporting OAuth2, MFA, sessions, and RBAC while maintaining backward compatibility.

- [ ] TASK-001: Create `migrations/versions/XXX_add_oauth_tables.py` with tables: `oauth_clients`, `oauth_authorization_codes`, `oauth_access_tokens`, `oauth_refresh_tokens`
- [ ] TASK-002: Create `migrations/versions/XXX_add_mfa_tables.py` with tables: `user_mfa_secrets`, `user_mfa_backup_codes`
- [ ] TASK-003: Create `migrations/versions/XXX_add_sessions_table.py` with table: `user_sessions` (session_id, user_id, refresh_token_jti, device_info, ip_address, expires_at, revoked_at)
- [ ] TASK-004: Create `migrations/versions/XXX_add_social_accounts_table.py` with table: `user_social_accounts` (provider, provider_user_id, access_token, refresh_token)
- [ ] TASK-005: Create `migrations/versions/XXX_add_rbac_tables.py` with tables: `roles`, `permissions`, `user_roles`, `role_permissions`
- [ ] TASK-006: Create `migrations/versions/XXX_add_audit_log_table.py` with table: `audit_logs` (event_type, user_id, ip_address, user_agent, metadata, created_at)
- [ ] TASK-007: Add indexes on frequently queried columns: `user_sessions.user_id`, `user_sessions.expires_at`, `audit_logs.user_id`, `audit_logs.created_at`

**Completion criteria**: All migrations run successfully on both SQLite and PostgreSQL, schema validates with `alembic check`

**Commit**: `feat: add database schema for OAuth2, MFA, sessions, RBAC, and audit logging`

---

### Phase 2: Core Authentication Services

**Goal**: Implement service layer with repository pattern and dependency injection.

- [ ] TASK-001: Create `app/auth/repositories/user_repository.py` with methods: `find_by_id`, `find_by_username`, `find_by_email`, `create`, `update`, `delete`
- [ ] TASK-002: Create `app/auth/repositories/session_repository.py` with methods: `create_session`, `find_by_refresh_token_jti`, `revoke_session`, `revoke_all_user_sessions`
- [ ] TASK-003: Create `app/auth/repositories/oauth_repository.py` with methods: `find_client_by_id`, `create_authorization_code`, `consume_authorization_code`
- [ ] TASK-004: Create `app/auth/services/auth_service.py` with methods: `authenticate_user`, `register_user`, `change_password`
- [ ] TASK-005: Create `app/auth/services/session_service.py` with methods: `create_session`, `refresh_session`, `revoke_session`, `list_active_sessions`
- [ ] TASK-006: Create `app/auth/services/mfa_service.py` with methods: `enable_mfa`, `verify_totp`, `generate_backup_codes`, `verify_backup_code`
- [ ] TASK-007: Create `app/auth/services/oauth_service.py` with methods: `authorize_client`, `exchange_code_for_token`, `validate_token`
- [ ] TASK-008: Create `app/auth/services/social_service.py` with methods: `get_oauth_url`, `exchange_code_for_user_info`, `link_social_account`

**Completion criteria**: All services have 90%+ test coverage, integration tests pass with real database

**Commit**: `feat: implement authentication service layer with repository pattern`

---

### Phase 3: OAuth2 & OIDC Implementation

**Goal**: Implement OAuth2 authorization code flow with PKCE and OIDC discovery.

- [ ] TASK-001: Create `app/auth/oauth/dependencies.py` with dependency: `ClientAuthenticated` (validates client_id + client_secret or JWT assertion)
- [ ] TASK-002: Create `app/auth/oauth/pkce.py` with functions: `generate_code_verifier`, `generate_code_challenge`, `verify_code_challenge`
- [ ] TASK-003: Create `app/auth/oauth/router.py` with endpoints: `POST /oauth/authorize`, `POST /oauth/token`, `GET /.well-known/openid-configuration`
- [ ] TASK-004: Create `app/auth/oauth/discovery.py` with OIDC discovery handler returning: issuer, authorization_endpoint, token_endpoint, jwks_uri, scopes_supported, response_types_supported
- [ ] TASK-005: Create `app/auth/oauth/jwks.py` with endpoint: `GET /.well-known/jwks.json` returning public keys in JWKS format
- [ ] TASK-006: Create `app/auth/oauth/models.py` with models: `OAuthClient`, `AuthorizationCodeRequest`, `TokenRequest`, `TokenResponse`
- [ ] TASK-007: Update `app/auth/deps.py` with scope validation: `RequiredScopes(scopes=["openid", "profile", "email"])`
- [ ] TASK-008: Add rate limiting: `Depends(RateLimiter(times=20, seconds=60))` to `/oauth/token` endpoint

**Completion criteria**: OAuth2 flows pass [OAuth 2.0 for Native Apps Best Current Practice](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-native-apps-13) test suite, OIDC discovery returns valid spec

**Commit**: `feat: implement OAuth2 authorization code flow with PKCE and OIDC discovery`

---

### Phase 4: Multi-Factor Authentication (MFA)

**Goal**: Implement TOTP-based MFA with backup codes and management endpoints.

- [ ] TASK-001: Install dependencies: `pyotp`, `qrcode`, `pillow` for TOTP generation and QR codes
- [ ] TASK-002: Create `app/auth/mfa/router.py` with endpoints: `POST /auth/mfa/setup`, `POST /auth/mfa/verify`, `DELETE /auth/mfa/disable`
- [ ] TASK-003: Create `app/auth/mfa/models.py` with models: `MfaSetupResponse`, `MfaVerifyRequest`, `MfaBackupCodesResponse`
- [ ] TASK-004: Update `app/auth/router.py` login endpoint to return `mfa_required: true` if user has MFA enabled, add `POST /auth/login/mfa` endpoint
- [ ] TASK-005: Create `app/auth/mfa/totp.py` with functions: `generate_secret`, `generate_qr_code_uri`, `verify_totp`
- [ ] TASK-006: Create `app/auth/mfa/backup_codes.py` with functions: `generate_backup_codes`, `hash_backup_codes`, `verify_backup_code`
- [ ] TASK-007: Add MFA enforcement option to config: `settings.mfa_required_for_all_users = False`
- [ ] TASK-008: Update `make_tokens` to include `amr` (Authentication Methods References) claim: `["pwd", "mfa"]`

**Completion criteria**: TOTP codes generated by Google Authenticator verify successfully, backup codes work as fallback

**Commit**: `feat: implement TOTP-based multi-factor authentication with backup codes`

---

### Phase 5: Session Management

**Goal**: Implement session tracking, listing, and revocation capabilities.

- [ ] TASK-001: Create `app/auth/sessions/router.py` with endpoints: `GET /auth/sessions`, `DELETE /auth/sessions/{session_id}`, `DELETE /auth/sessions`
- [ ] TASK-002: Create `app/auth/sessions/models.py` with models: `SessionResponse`, `SessionsListResponse`
- [ ] TASK-003: Create `app/auth/sessions/device_info.py` with function: `parse_user_agent(request)` extracting browser, OS, device type
- [ ] TASK-004: Update `app/auth/services/session_service.py` to store device info and IP address on session creation
- [ ] TASK-005: Create middleware: `app/auth/sessions/middleware.py` with `ValidateSession` dependency checking session not revoked
- [ ] TASK-006: Update `POST /auth/refresh` to check session not revoked before issuing new tokens
- [ ] TASK-007: Add session cleanup job: `app/auth/sessions/cleanup.py` with `delete_expired_sessions` run via cron or Celery
- [ ] TASK-008: Add WebSocket support for real-time session revocation notifications

**Completion criteria**: Users can list all active sessions, revoke individual sessions, all sessions update immediately on revocation

**Commit**: `feat: implement session management with device tracking and revocation`

---

### Phase 6: Social Login Integration

**Goal**: Implement OAuth2 social login for Google, GitHub, GitLab.

- [ ] TASK-001: Create `app/auth/social/config.py` with provider configs: `google`, `github`, `gitlab` containing client_id, client_secret, redirect_uri, scopes
- [ ] TASK-002: Create `app/auth/social/router.py` with endpoints: `GET /auth/social/{provider}/authorize`, `GET /auth/social/{provider}/callback`
- [ ] TASK-003: Create `app/auth/social/providers/base.py` with abstract class: `SocialAuthProvider` defining `get_authorization_url`, `exchange_code_for_tokens`, `get_user_info`
- [ ] TASK-004: Create `app/auth/social/providers/google.py` implementing Google OAuth2 flow
- [ ] TASK-005: Create `app/auth/social/providers/github.py` implementing GitHub OAuth flow
- [ ] TASK-006: Create `app/auth/social/providers/gitlab.py` implementing GitLab OAuth flow
- [ ] TASK-007: Update `app/auth/services/social_service.py` with methods: `handle_social_login`, `auto_create_user_on_social_login`
- [ ] TASK-008: Add social account linking: `POST /auth/social/link`, `GET /auth/social/linked`, `DELETE /auth/social/unlink`

**Completion criteria**: Social login flow works end-to-end for all three providers, auto-creates users on first login

**Commit**: `feat: implement social login for Google, GitHub, GitLab`

---

### Phase 7: Role-Based Access Control (RBAC)

**Goal**: Implement flexible RBAC system with roles and permissions.

- [ ] TASK-001: Create `app/auth/rbac/models.py` with models: `Role`, `Permission`, `UserRole`, `RolePermission`, `CreateRoleRequest`, `UpdateRoleRequest`
- [ ] TASK-002: Create `app/auth/rbac/repositories/role_repository.py` with methods: `find_by_name`, `create`, `update`, `delete`, `assign_to_user`, `remove_from_user`
- [ ] TASK-003: Create `app/auth/rbac/repositories/permission_repository.py` with methods: `create`, `find_by_resource_and_action`, `assign_to_role`, `remove_from_role`
- [ ] TASK-004: Create `app/auth/rbac/router.py` with endpoints: `POST /auth/roles`, `GET /auth/roles`, `POST /auth/roles/{role_id}/permissions`
- [ ] TASK-005: Create `app/auth/rbac/dependencies.py` with dependencies: `RequirePermissions(perms)`, `RequireRoles(roles)`
- [ ] TASK-00VI: Seed default roles and permissions in migration: `admin`, `user`, `moderator` with appropriate permissions
- [ ] TASK-007: Add permissions to access token claims: `permissions: ["read:own", "update:own"]`
- [ ] TASK-008: Update `/auth/me` endpoint to return user's roles and permissions

**Completion criteria**: Users can be assigned roles, roles can be assigned permissions, endpoint access is controlled by permissions

**Commit**: `feat: implement role-based access control (RBAC) system`

---

### Phase 8: Security Hardening

**Goal**: Implement brute-force protection, account lockout, and additional security measures.

- [ ] TASK-001: Create `app/auth/security/brute_force.py` with `BruteForceProtection` class tracking failed attempts per IP and username
- [ ] TASK-002: Create `app/auth/security/lockout.py` with functions: `lock_account`, `is_account_locked`, `unlock_account`
- [ ] TASK-003: Update `app/auth/router.py` login endpoint to use brute-force protection, return 429 if threshold exceeded
- [ ] TASK-004: Create `app/auth/security/password_history.py` with functions: `check_password_not_reused`, `add_password_to_history`
- [ ] TASK-005: Add password expiration check: `if user.password_expires_at < now: raise PasswordExpiredError`
- [ ] TASK-006: Implement secure token storage: encrypt refresh tokens in database using Fernet or AES-256-GCM
- [ ] TASK-007: Add CSRF protection for state-changing endpoints: `Depends(csrf_check)`
- [ ] TASK-008: Implement token binding: bind tokens to IP address or session ID, validate on refresh

**Completion criteria**: Brute-force attacks are blocked after 5 failed attempts, accounts lock for 15 minutes, passwords must not reuse last 5

**Commit**: `feat: implement brute-force protection, account lockout, and security hardening`

---

### Phase 9: Audit Logging & Compliance

**Goal**: Implement comprehensive audit logging for security events and compliance.

- [ ] TASK-001: Create `app/auth/audit/logger.py` with `audit_log(event_type, user_id, ip_address, metadata)` function
- [ ] TASK-002: Create `app/auth/audit/events.py` with event types: `login_success`, `login_failed`, `mfa_enabled`, `password_changed`, `session_revoked`
- [ ] TASK-003: Update all auth endpoints to emit audit logs on security-relevant events
- [ ] TASK-00IV: Create `app/auth/audit/router.py` with endpoint: `GET /auth/audit/logs` with filters by user, date_range, event_type
- [ ] TASK-005: Add audit log export: `GET /auth/audit/logs/export` returning CSV or JSON
- [ ] TASK-006: Implement audit log retention policy: delete logs older than 90 days (configurable)
- [ ] TASK-007: Add PII masking for sensitive data in audit logs: mask email addresses, partial IPs
- [ ] TASK-008: Create `app/auth/audit/reports.py` with compliance reports: failed login attempts, MFA adoption rate, active sessions

**Completion criteria**: All auth events emit structured audit logs, logs can be exported for compliance, retention policy enforces deletion

**Commit**: `feat: implement comprehensive audit logging and compliance reporting`

---

### Phase 10: Admin Dashboard & APIs

**Goal**: Create admin APIs and basic dashboard for user and session management.

- [ ] TASK-001: Create `app/admin/router.py` with endpoints: `GET /admin/users`, `GET /admin/users/{user_id}`, `PATCH /admin/users/{user_id}`, `DELETE /admin/users/{user_id}`
- [ ] TASK-002: Create `app/admin/models.py` with models: `UserListResponse`, `UserDetailResponse`, `UpdateUserRequest`
- [ ] TASK-003: Create `app/admin/services/user_management.py` with methods: `list_users`, `get_user_detail`, `lock_user`, `unlock_user`, `force_password_reset`
- [ ] TASK-004: Add admin dependencies: `RequireAdminRole` to all admin endpoints
- [ ] TASK-005: Create `app/admin/dashboard.py` with endpoint: `GET /admin/dashboard` returning metrics: total_users, active_sessions, mfa_enabled_users, failed_login_attempts_24h
- [ ] TASK-006: Create admin panel: `templates/admin/dashboard.html` with user table, session viewer, audit log viewer
- [ ] TASK-007: Add pagination and filtering to user list: `GET /admin/users?page=1&limit=50&search=username&status=active`
- [ ] TASK-008: Add bulk operations: `POST /admin/users/bulk-lock`, `POST /admin/users/bulk-delete`

**Completion criteria**: Admins can manage users, view dashboard metrics, export audit logs via UI and API

**Commit**: `feat: implement admin APIs and dashboard for user management`

---

### Phase 11: Observability & Monitoring

**Goal**: Enhance metrics, tracing, and alerting for production operations.

- [ ] TASK-001: Update `app/core/metrics.py` with metrics: `auth_mfa_attempts_total`, `auth_social_logins_total`, `auth_sessions_active`, `auth_brute_force_blocks_total`
- [ ] TASK-002: Create `app/core/tracing.py` with OpenTelemetry setup for distributed tracing
- [ ] TASK-003: Add span attributes to auth operations: `user.id`, `auth.method`, `oauth.provider`, `mfa.success`
- [ ] TASK-004: Create health check for external dependencies: `GET /healthz/ready` checks database, redis, external OAuth providers
- [ ] TASK-005: Create Grafana dashboard JSON: `docs/grafana/fastauth-dashboard.json` with panels for auth metrics
- [ ] TASK-006: Add Prometheus alerts: `alerts.yml` with rules for high failed login rate, high MFA failure rate, brute-force attacks
- [ ] TASK-007: Create `app/core/profiling.py` with PyProfiler setup for performance profiling
- [ ] TASK-008: Add structured logging with correlation IDs: update log format to include `request_id`, `user_id`, `trace_id`

**Completion criteria**: All auth operations emit metrics, traces show full request flow, Prometheus alerts fire on anomalies

**Commit**: `feat: enhance observability with metrics, tracing, and alerting`

---

### Phase 12: Testing & Documentation

**Goal**: Comprehensive test coverage and production-ready documentation.

- [ ] TASK-001: Create integration tests for OAuth2 flow: `tests/test_oauth_integration.py` testing authorization code flow with PKCE
- [ ] TASK-002: Create integration tests for MFA: `tests/test_mfa_integration.py` testing TOTP setup, verification, backup codes
- [ ] TASK-003: Create integration tests for social login: `tests/test_social_integration.py` for each provider
- [ ] TASK-004: Create security tests: `tests/test_security.py` testing brute-force protection, CSRF, token binding, session revocation
- [ ] TASK-005: Create load tests with k6: `tests/load/auth_flow.js` simulating 1000 concurrent logins, 5000 token refreshes
- [ ] TASK-006: Create API documentation: `docs/api/oauth2.md`, `docs/api/mfa.md`, `docs/api/social.md`, `docs/api/admin.md`
- [ ] TASK-007: Create deployment guide: `docs/deployment/production.md` covering Docker Compose, Kubernetes, environment variables
- [ ] TASK-008: Create security guide: `docs/security/best_practices.md` covering rate limiting, brute-force protection, secrets management

**Completion criteria**: 90%+ test coverage, all integration tests pass, load tests handle 1000 RPS, documentation is comprehensive

**Commit**: `test: add comprehensive integration tests, load tests, and documentation`

---

## 3. Alternatives Considered

- **ALT-001**: Use existing open-source solution (Keycloak, Authentik, Supabase) — rejected because we need custom integration, full control over auth flow, and learning experience
- **ALT-002**: Build monolithic auth service — rejected because microservices architecture allows independent scaling and deployment
- **ALT-003**: Use JWT only without session management — rejected because sessions provide security (revocation), auditability, and better user experience
- **ALT-004**: Skip social login initially — rejected because social login is expected feature for modern auth systems, reduces friction

## 4. Dependencies

- **DEP-001**: FastAPI 0.100+ — web framework with async support
- **DEP-002**: PostgreSQL 14+ — production database (SQLite for dev)
- **DEP-003**: Redis 7+ — rate limiting, session caching, pub/sub for real-time events
- **DEP-004**: pyotp — TOTP generation and verification
- **DEP-005**: authlib — OAuth2 and OIDC implementation library
- **DEP-006**: httpx — async HTTP client for social login provider API calls
- **DEP-007**: Prometheus — metrics collection and alerting
- **DEP-008**: OpenTelemetry — distributed tracing

## 5. Affected Files

- **FILE-001**: `app/auth/router.py` — add MFA login endpoint, update login flow
- **FILE-002**: `app/auth/models.py` — add OAuth2, MFA, social login models
- **FILE-003**: `app/auth/deps.py` — add OAuth2 client auth, RBAC dependencies
- **FILE-004**: `app/core/security.py` — add token encryption, CSRF protection
- **FILE-005**: `app/core/config.py` — add OAuth2, MFA, social provider configs
- **FILE-006**: `main.py` — include new routers for OAuth2, MFA, admin
- **FILE-007**: `tests/test_auth.py` — expand test coverage for new features

## 6. Testing

- [ ] TEST-001: Integration tests for OAuth2 authorization code flow with PKCE in `tests/test_oauth_integration.py`
- [ ] TEST-002: Integration tests for TOTP setup and verification in `tests/test_mfa_integration.py`
- [ ] TEST-003: Integration tests for social login providers in `tests/test_social_integration.py`
- [ ] TEST-004: Security tests for brute-force protection, CSRF, token binding in `tests/test_security.py`
- [ ] TEST-005: Load tests with k6 for 1000 concurrent logins in `tests/load/auth_flow.js`
- [ ] TEST-006: Manual verification of session revocation in UI
- [ ] TEST-007: Manual verification of MFA flow with authenticator app
- [ ] TEST-008: Manual verification of social login with Google, GitHub, GitLab

## 7. Risks & Assumptions

- **RISK-001**: OAuth2 implementation complexity — mitigation: use authlib library, reference RFC specifications, extensive testing
- **RISK-002**: Social login provider API changes — mitigation: version provider client libraries, monitor for deprecations
- **RISK-003**: MFA user experience friction — mitigation: make MFA optional by default, provide clear setup instructions, offer backup codes
- **RISK-004**: Session storage scalability — mitigation: use Redis for session cache, implement cleanup job, monitor storage growth
- **RISK-005**: Security vulnerabilities in custom auth implementation — mitigation: security audit, follow OWASP guidelines, extensive testing
- **ASSUM-001**: PostgreSQL available in production (SQLite for development)
- **ASSUM-002**: Redis available for rate limiting and session caching
- **ASSUM-003**: External OAuth providers (Google, GitHub, GitLab) remain available

## 8. Architecture Diagram

```mermaid
graph TB
    subgraph Clients
        Web[Web App]
        Mobile[Mobile App]
        SPA[SPA]
    end
    
    subgraph API[FastAuth API]
        Router[API Gateway]
        OAuth[OAuth2/OIDC]
        MFA[MFA Service]
        Social[Social Login]
        Session[Session Service]
        RBAC[RBAC Service]
        Admin[Admin API]
    end
    
    subgraph Storage[(Data Layer)]
        PG[(PostgreSQL)]
        Redis[(Redis)]
    end
    
    subgraph External[External Services]
        Google[Google OAuth]
        GitHub[GitHub OAuth]
        GitLab[GitLab OAuth]
    end
    
    subgraph Observability[Monitoring]
        Prometheus[Prometheus]
        Grafana[Grafana]
        Jaeger[Jaeger/OTel]
    end
    
    Web -->|HTTPS| Router
    Mobile -->|HTTPS| Router
    SPA -->|HTTPS| Router
    
    Router --> OAuth
    Router --> MFA
    Router --> Social
    Router --> Session
    Router --> RBAC
    Router --> Admin
    
    OAuth --> PG
    MFA --> PG
    Social --> PG
    Session --> PG
    RBAC --> PG
    Admin --> PG
    
    Session --> Redis
    
    Social --> Google
    Social --> GitHub
    Social --> GitLab
    
    Router --> Prometheus
    Router --> Jaeger
    Prometheus --> Grafana
```

## 9. Related Specs & Further Reading

- [RFC 6749: OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)
- [RFC 7636: PKCE](https://datatracker.ietf.org/doc/html/rfc7636)
- [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OAuth 2.0 for Native Apps Best Current Practice](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-native-apps-13)
- [RFC 6238: TOTP](https://datatracker.ietf.org/doc/html/rfc6238)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
