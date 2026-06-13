from prometheus_client import Counter, Gauge, Histogram

http_requests_total = Counter(
    "fastauth_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "fastauth_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

auth_registrations_total = Counter(
    "fastauth_auth_registrations_total",
    "Total user registrations",
)

auth_login_attempts_total = Counter(
    "fastauth_auth_login_attempts_total",
    "Total login attempts",
    ["success"],
)

auth_token_refreshes_total = Counter(
    "fastauth_auth_token_refreshes_total",
    "Total token refreshes",
)

# New metrics for MFA, social login, sessions, and security
auth_mfa_attempts_total = Counter(
    "fastauth_auth_mfa_attempts_total",
    "Total MFA verification attempts",
    ["success"],
)

auth_social_logins_total = Counter(
    "fastauth_auth_social_logins_total",
    "Total social login attempts",
    ["provider", "success"],
)

auth_sessions_active = Gauge(
    "fastauth_auth_sessions_active",
    "Currently active (non-revoked, non-expired) sessions",
)

auth_brute_force_blocks_total = Counter(
    "fastauth_auth_brute_force_blocks_total",
    "Total requests blocked by brute-force protection",
)
