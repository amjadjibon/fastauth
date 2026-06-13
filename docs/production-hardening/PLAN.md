---
goal: Harden fastauth for production — security, resilience, CI/CD, and observability gaps
version: 1.0
date_created: 2026-06-12
last_updated: 2026-06-12
owner: amjadjibon
status: 'In progress'
tags: [architecture, feature, chore]
---

# Production Hardening Plan

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

fastauth already has structured logging, OpenTelemetry tracing, Prometheus metrics, rate limiting, and a passing test suite. This plan closes the remaining gaps — security headers, CI/CD pipeline, trace-log correlation, alerting, and operational resilience — required before running in production.

## 1. Requirements & Constraints

- **REQ-001**: Every HTTP response must include security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options).
- **REQ-002**: CORS must be restricted to an explicit allowlist, not wildcard.
- **REQ-003**: Logs and traces must be correlatable by trace ID without manual effort.
- **REQ-004**: CI must block merges when lint, type-check, or tests fail.
- **REQ-005**: Prometheus must fire alerts on sustained 5xx rate and high latency.
- **REQ-006**: App startup must survive transient DB unavailability without crashing.
- **CON-001**: No new required runtime dependencies — use packages already in the venv where possible.
- **CON-002**: All changes must keep `ruff check`, `ty check`, and `pytest` green.
- **GUD-001**: Each phase is a single git commit with a clear message.
- **PAT-001**: Feature flags via env vars — all new behaviour off by default.

## 2. Implementation Steps

> **Agent instructions**: Before each phase, run `jj new`. After completing all tasks in a phase, run `jj describe -m "<type>: <phase summary>"`. Update checkboxes to `[x]` as each task is completed.

---

### Phase 1: Security Headers & CORS

**Goal**: Harden every HTTP response and lock down cross-origin access before any other work ships.

- [ ] TASK-001: Add `SecurityHeadersMiddleware` to `app/core/middleware.py`. On every response set: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(), microphone=()`. For HTTPS only, also set `Strict-Transport-Security: max-age=63072000; includeSubDomains`.
- [ ] TASK-002: Add `CORSMiddleware` from `fastapi.middleware.cors` in `main.py`. Read allowed origins from a new `cors_origins: list[str]` setting in `app/core/config.py`; default to `[]` (deny all cross-origin). Register it before `RequestIDMiddleware`.
- [ ] TASK-003: Add `CORS_ORIGINS` to the app's `environment` block in `compose.yaml` with value `""` (empty, restrictive default).
- [ ] TASK-004: Write two tests in `tests/test_security.py`: (a) any response has all four security headers; (b) a cross-origin request from an unlisted origin receives no `Access-Control-Allow-Origin` header.

**Completion criteria**: `pytest tests/test_security.py` passes; `curl -I http://localhost:8000/livez` shows all four headers.

**jj commit**: `jj describe -m "feat: security headers and CORS middleware"`

---

### Phase 2: Trace ID in Logs

**Goal**: Every log line emitted during a request includes the active OTel trace ID so logs and Jaeger traces can be joined without manual effort.

- [ ] TASK-005: In `app/core/middleware.py`, after `call_next` returns in `LoggerMiddleware`, read the current span via `trace.get_current_span()` and extract `trace_id = format(span.get_span_context().trace_id, "032x")` (returns `"0" * 32` when no span is active — treat that as `None`). Add `trace_id` to the `extra` dict passed to the logger.
- [ ] TASK-006: Add `%(trace_id)s` to the `fmt` string in `conf/log.yaml` so it appears in every JSON access log line.
- [ ] TASK-007: Add one test in `tests/test_security.py`: with `OTEL_ENABLED=false`, `trace_id` is absent or `None` in the log record; presence check when enabled is covered by integration.

**Completion criteria**: A request with OTel enabled produces a log line with a 32-char hex `trace_id` field matching the span visible in Jaeger.

**jj commit**: `jj describe -m "feat: inject trace ID into access log lines"`

---

### Phase 3: Startup Resilience

**Goal**: Prevent the app from crash-looping when the database is momentarily unavailable at startup.

- [ ] TASK-008: In `main.py`, wrap the `_migrate()` call inside `lifespan` with a retry loop: attempt up to 10 times with 2-second backoff, catching `sqlalchemy.exc.OperationalError`. Log each retry at `WARNING` level with attempt number. Raise after the final attempt so the container still exits non-zero on genuine failure.
- [ ] TASK-009: In `app/core/db.py`, set explicit pool parameters on `create_async_engine`: `pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=1800`. Add a comment explaining `pool_recycle` prevents stale connections from PgBouncer or load-balancer idle timeouts.
- [ ] TASK-010: In `compose.yaml`, add `restart: on-failure` (already set) and tune the `app` service healthcheck: `test: ["CMD", "curl", "-f", "http://localhost:8000/livez"]`, `interval: 10s`, `timeout: 5s`, `retries: 3`, `start_period: 15s`.

**Completion criteria**: Starting `docker compose up` with the DB container stopped causes the app to log retry warnings and eventually fail cleanly, not crash immediately with an unhandled exception. Once DB starts, app recovers.

**jj commit**: `jj describe -m "feat: startup retry and connection pool tuning"`

---

### Phase 4: Prometheus Alert Rules

**Goal**: Prometheus fires an alert when the 5xx error rate exceeds 1% over 5 minutes, or p99 latency exceeds 2 seconds.

- [ ] TASK-011: Create `conf/prometheus/alerts.yml` with two rules:
  - `FastauthHighErrorRate`: fires when `rate(fastauth_http_requests_total{status_code=~"5.."}[5m]) / rate(fastauth_http_requests_total[5m]) > 0.01` for 5 minutes. Severity: `critical`.
  - `FastauthHighLatency`: fires when `histogram_quantile(0.99, rate(fastauth_http_request_duration_seconds_bucket[5m])) > 2` for 5 minutes. Severity: `warning`.
- [ ] TASK-012: Update `conf/prometheus.yml` to reference the rules file: add `rule_files: ["alerts.yml"]` and update the Prometheus `command` in `compose.yaml` to mount `./conf/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro`. Move `prometheus.yml` to `conf/prometheus/prometheus.yml` and update the mount path accordingly.

**Completion criteria**: `docker compose exec prometheus promtool check rules /etc/prometheus/alerts.yml` exits 0.

**jj commit**: `jj describe -m "feat: Prometheus alert rules for error rate and latency"`

---

### Phase 5: CI/CD Pipeline

**Goal**: Every push and pull request runs lint, type-check, and tests automatically; a failed check blocks merge.

- [ ] TASK-013: Create `.github/workflows/ci.yml` with a single job `test` running on `ubuntu-latest`, triggered on `push` and `pull_request` to `main`. Steps: checkout → install uv → `uv sync --frozen` → `uv run ruff check .` → `uv run ty check` → `uv run pytest tests/ -q`.
- [ ] TASK-014: Add a second job `build` (depends on `test`) that runs `docker build .` to verify the image builds. No push — image publishing is a separate concern.
- [ ] TASK-015: Add `.github/workflows/deps.yml`: a weekly Dependabot-style workflow using `uv lock --upgrade` + `git commit + push` on a branch, or alternatively add a `dependabot.yml` config for the `pip` ecosystem targeting `pyproject.toml`.

**Completion criteria**: Opening a PR with a deliberate `ruff` violation causes the CI job to fail with a non-zero exit. A clean PR shows all green checks.

**jj commit**: `jj describe -m "chore: GitHub Actions CI pipeline"`

---

## 3. Alternatives Considered

- **ALT-001**: Use `slowapi` for rate limiting instead of the custom implementation — rejected because the existing limiter is already wired and tested; adding a dependency for equivalent functionality adds no value.
- **ALT-002**: Add Loki for log aggregation in Phase 2 — deferred (not rejected); Loki requires Promtail configuration and a separate volume, making it a self-contained phase. Trace-ID injection is the higher-value immediate win.
- **ALT-003**: Use `tenacity` for retry logic in Phase 3 — rejected because the retry loop is simple enough to inline without a new dependency (CON-001).
- **ALT-004**: Alertmanager + PagerDuty integration — deferred; alert rules fire into Alertmanager but routing to an on-call tool is environment-specific and outside this plan's scope.

## 4. Dependencies

- **DEP-001**: `fastapi.middleware.cors.CORSMiddleware` — already available via `fastapi`.
- **DEP-002**: `opentelemetry.trace` — already installed via `opentelemetry-sdk`.
- **DEP-003**: `sqlalchemy.exc.OperationalError` — already available via `sqlalchemy`.
- **DEP-004**: GitHub Actions runners — requires the repo to be on GitHub with Actions enabled.
- **DEP-005**: `promtool` — ships inside the `prom/prometheus` Docker image; no local install needed.

## 5. Affected Files

- **FILE-001**: `app/core/middleware.py` — add `SecurityHeadersMiddleware`, inject `trace_id` into `LoggerMiddleware`
- **FILE-002**: `app/core/config.py` — add `cors_origins` setting
- **FILE-003**: `main.py` — register `CORSMiddleware` and `SecurityHeadersMiddleware`; add DB retry loop in `lifespan`
- **FILE-004**: `app/core/db.py` — add pool parameters to `create_async_engine`
- **FILE-005**: `conf/log.yaml` — add `%(trace_id)s` to formatter `fmt`
- **FILE-006**: `conf/prometheus/alerts.yml` — new file with alert rules
- **FILE-007**: `conf/prometheus/prometheus.yml` — moved from `conf/prometheus.yml`, add `rule_files`
- **FILE-008**: `compose.yaml` — update Prometheus mount path, add app healthcheck, add `CORS_ORIGINS`
- **FILE-009**: `tests/test_security.py` — new file, security header and CORS tests
- **FILE-010**: `.github/workflows/ci.yml` — new file, CI pipeline

## 6. Testing

- [ ] TEST-001: `tests/test_security.py` — assert all four security headers present on `GET /livez`
- [ ] TEST-002: `tests/test_security.py` — assert no `Access-Control-Allow-Origin` for unlisted origin
- [ ] TEST-003: `tests/test_security.py` — assert `trace_id` key absent (or `None`) in log record when OTel disabled
- [ ] TEST-004: Manual — `docker compose exec prometheus promtool check rules /etc/prometheus/alerts.yml`
- [ ] TEST-005: Manual — open a PR with a ruff error, confirm CI fails

## 7. Risks & Assumptions

- **RISK-001**: `SecurityHeadersMiddleware` may break the Swagger UI (`/docs`) if `Content-Security-Policy` is too strict — mitigation: omit CSP from the initial implementation; add it in a follow-up once the policy is tuned against the actual asset URLs.
- **RISK-002**: DB retry loop in `lifespan` may mask genuine misconfiguration errors by retrying indefinitely — mitigation: cap at 10 attempts (TASK-008) and re-raise, ensuring non-zero exit.
- **RISK-003**: Moving `conf/prometheus.yml` to `conf/prometheus/prometheus.yml` (TASK-012) changes the Docker Compose mount path — mitigation: update both `compose.yaml` and the Dockerfile `COPY` in the same commit.
- **ASSUMPTION-001**: The repo is hosted on GitHub with Actions enabled — TASK-013 through TASK-015 are no-ops otherwise.
- **ASSUMPTION-002**: OTel is enabled in the Docker Compose environment (`OTEL_ENABLED=true`) — trace ID injection in logs is a no-op when `OTEL_ENABLED=false`.

## 8. Architecture Diagram

```
                          Request
                             │
                             ▼
                   ┌──────────────────┐
                   │ SecurityHeaders  │  ← Phase 1 (new)
                   │   Middleware     │
                   └────────┬─────────┘
                            │
                   ┌────────▼─────────┐
                   │  CORS Middleware  │  ← Phase 1 (new)
                   └────────┬─────────┘
                            │
                   ┌────────▼─────────┐
                   │  RequestID MW    │
                   └────────┬─────────┘
                            │
                   ┌────────▼─────────┐
                   │  Metrics MW      │
                   └────────┬─────────┘
                            │
                   ┌────────▼─────────┐
                   │  Logger MW       │  ← Phase 2: + trace_id
                   └────────┬─────────┘
                            │
                   ┌────────▼─────────┐
                   │  FastAPI Routes  │
                   └────────┬─────────┘
                            │
               ┌────────────┼────────────┐
               ▼            ▼            ▼
          PostgreSQL      Redis        (future)
          (pool tune      (rate        services
          Phase 3)        limit)

Observability pipeline:
  Logs  ──────────────────────────▶ stdout (JSON + trace_id)
  Traces ──OTLP──▶ Jaeger
  Metrics ◀─scrape─ Prometheus ──alert──▶ Alertmanager
                       │
                    Grafana
```

## 9. Related Specs & Further Reading

- `docs/production-hardening/PLAN.md` — this file
- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [OpenTelemetry Python trace context](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html)
- [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [uv GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/)
