---
goal: Grafana custom dashboard for fastauth observability
version: 1.0
date_created: 2026-06-13
last_updated: 2026-06-13

owner: amjadjibon
status: 'Completed'
tags: [feature, architecture]
---

# Grafana Custom Dashboard for fastauth

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

Build a provisioned Grafana dashboard that gives operators a single-pane view of fastauth health, authentication activity, and security signals. The dashboard is delivered as a JSON file under `conf/grafana/provisioning/dashboards/` so it loads automatically on `docker compose up` without manual import.

## 1. Requirements & Constraints

- **REQ-001**: Dashboard must use only metrics already emitted by `app/core/metrics.py` — no new instrumentation needed.
- **REQ-002**: Cover four concern areas: HTTP traffic, auth activity, session health, and security signals.
- **REQ-003**: Dashboard JSON must be valid Grafana 10+ format and provisioned via the existing datasource `Prometheus`.
- **CON-001**: No Grafana UI edits — all config lives in `conf/grafana/provisioning/dashboards/` and is version-controlled.
- **CON-002**: Jaeger traces are available but this dashboard focuses on Prometheus metrics; trace links are a bonus.
- **GUD-001**: Use `$__rate_interval` for all `rate()` queries so they auto-adapt to the scrape interval.
- **GUD-002**: Every panel title should be self-explanatory without hovering.

## 2. Implementation Steps

> **Agent instructions**: This repo uses git, not jj. Use `git add -A && git commit -m "<message>"` at each phase boundary. Update checkboxes to `[x]` as each task is completed.

### Phase 1: Grafana Dashboard Provisioning Config

**Goal**: Wire up the dashboard auto-loader so any JSON file placed in the dashboards folder is picked up on startup.

- [x] TASK-001: Create `conf/grafana/provisioning/dashboards/dashboards.yml` with provider config pointing to `/etc/grafana/dashboards` folder, `disableDeletion: false`, `updateIntervalSeconds: 30`.
- [x] TASK-002: Update `compose.telemetry.yaml` grafana service: add volume mount `./conf/grafana/provisioning/dashboards:/etc/grafana/dashboards:ro` alongside the existing provisioning mount.

**Completion criteria**: `docker compose -f compose.yaml -f compose.telemetry.yaml up grafana` starts without errors; Grafana UI shows "Dashboards" provisioning source in Configuration → Data sources.

**git commit**: `git add -A && git commit -m "chore: add Grafana dashboard provisioning config"`

---

### Phase 2: HTTP Traffic Row

**Goal**: Build the first row of panels covering overall request volume, error rate, and latency percentiles.

Metrics available: `fastauth_http_requests_total{method, path, status_code}`, `fastauth_http_request_duration_seconds_bucket{method, path}`.

- [x] TASK-003: Create `conf/grafana/provisioning/dashboards/fastauth.json` with dashboard skeleton: `title: "fastauth"`, uid `fastauth`, `schemaVersion: 39`, refresh `15s`, datasource variable.
- [x] TASK-004: Add **Row** panel: `HTTP Traffic`.
- [x] TASK-005: Add **Stat** panel `Request Rate` — query: `sum(rate(fastauth_http_requests_total[$__rate_interval]))`, unit `reqps`.
- [x] TASK-006: Add **Stat** panel `Error Rate (5xx)` — query: ratio of 5xx to total, unit `percentunit`, thresholds green < 0.01, red ≥ 0.01.
- [x] TASK-007: Add **Time series** panel `Request Rate by Status` — three series split by 2xx/4xx/5xx status class.
- [x] TASK-008: Add **Time series** panel `Latency Percentiles` — p50/p95/p99 via `histogram_quantile`, unit `s`.

**Completion criteria**: Dashboard JSON is valid; panels render in Grafana with real data when the app is running.

**git commit**: `git add -A && git commit -m "feat: add HTTP traffic row to Grafana dashboard"`

---

### Phase 3: Auth Activity Row

**Goal**: Surface registration, login success/failure, token refresh, MFA, and social login rates.

Metrics available: `fastauth_auth_registrations_total`, `fastauth_auth_login_attempts_total{success}`, `fastauth_auth_token_refreshes_total`, `fastauth_auth_mfa_attempts_total{success}`, `fastauth_auth_social_logins_total{provider, success}`.

- [x] TASK-009: Add **Row** panel: `Auth Activity`.
- [x] TASK-010: Add **Stat** panel `Registrations / min` — query: `rate(fastauth_auth_registrations_total[$__rate_interval]) * 60`.
- [x] TASK-011: Add **Stat** panel `Login Success Rate` — ratio of successful to total login attempts, unit `percentunit`.
- [x] TASK-012: Add **Time series** panel `Login Attempts` — two series: success (green) and failed (red).
- [x] TASK-013: Add **Time series** panel `Token Refreshes / min`.
- [x] TASK-014: Add **Bar gauge** panel `Social Logins by Provider` — grouped by `provider` label.
- [x] TASK-015: Add **Stat** panel `MFA Success Rate` — ratio of successful to total MFA attempts, unit `percentunit`.

**Completion criteria**: All auth panels visible and labelled; login series correctly split by `success` label.

**git commit**: `git add -A && git commit -m "feat: add auth activity row to Grafana dashboard"`

---

### Phase 4: Session Health & Security Row

**Goal**: Show active session count and brute-force block rate so operators can spot anomalies.

Metrics available: `fastauth_auth_sessions_active` (Gauge), `fastauth_auth_brute_force_blocks_total`.

- [x] TASK-016: Add **Row** panel: `Sessions & Security`.
- [x] TASK-017: Add **Stat** panel `Active Sessions` — query: `fastauth_auth_sessions_active`, unit `short`.
- [x] TASK-018: Add **Time series** panel `Active Sessions Over Time`.
- [x] TASK-019: Add **Stat** panel `Brute-Force Blocks / min` — thresholds: green = 0, yellow > 1, red > 10.
- [x] TASK-020: Add **Time series** panel `Brute-Force Blocks Over Time`.

**Completion criteria**: Session gauge reflects actual session count from the DB; brute-force panel spikes correctly when test logins with bad passwords are sent.

**git commit**: `git add -A && git commit -m "feat: add sessions and security row to Grafana dashboard"`

---

### Phase 5: Top Endpoints Table & Alerts Annotations

**Goal**: Add a top-N slow/busy endpoints table and wire up Prometheus alert-state annotations so alert firings appear as vertical lines on time-series panels.

- [x] TASK-021: Add **Table** panel `Top Endpoints by Request Count` — top 10 by `sum by (method, path)`.
- [x] TASK-022: Add **Table** panel `Top Endpoints by p95 Latency` — top 10 by histogram_quantile 0.95, unit `s`.
- [x] TASK-023: Add dashboard-level annotation querying `ALERTS{alertname=~"Fastauth.*"}` from Prometheus — draws red lines on all time-series when an alert fires.

**Completion criteria**: Both tables populate with path-level data; triggering a test alert (temporarily lower threshold in `alerts.yml`) shows a red annotation line on all time-series panels.

**git commit**: `git add -A && git commit -m "feat: add top endpoints tables and alert annotations to dashboard"`

---

## 3. Alternatives Considered

- **ALT-001**: Import dashboard via Grafana UI — rejected because it's not version-controlled and lost on container rebuild.
- **ALT-002**: Use Grafonnet (Jsonnet) to generate the JSON — rejected because it adds a build step; raw JSON is simpler for a single dashboard.

## 4. Dependencies

- **DEP-001**: Grafana 10+ running via `compose.telemetry.yaml` — already in place.
- **DEP-002**: Prometheus scraping `app:8000/metrics` — already configured in `conf/prometheus/prometheus.yml`.
- **DEP-003**: All metrics in `app/core/metrics.py` emitted at runtime — already instrumented.

## 5. Affected Files

- **FILE-001**: `conf/grafana/provisioning/dashboards/dashboards.yml` — new, enables auto-provisioning
- **FILE-002**: `conf/grafana/provisioning/dashboards/fastauth.json` — new, the dashboard definition
- **FILE-003**: `compose.telemetry.yaml` — add dashboards volume mount to grafana service

## 6. Testing

- [x] TEST-001: Run `docker compose -f compose.yaml -f compose.telemetry.yaml up -d` and open `http://localhost:3000`; dashboard appears under Dashboards without manual import.
- [x] TEST-002: Hit `POST /auth/login` with wrong passwords 5× and verify the brute-force panel increments.
- [x] TEST-003: Validate dashboard JSON with `jq . conf/grafana/provisioning/dashboards/fastauth.json` — must exit 0. ✓ (verified: 20 unique panel IDs, valid JSON)
- [x] TEST-004: Temporarily set `FastauthHighErrorRate` threshold to `> 0` in `alerts.yml`, wait one scrape, confirm annotation line appears on the Request Rate time series.

## 7. Risks & Assumptions

- **RISK-001**: Panel IDs in the JSON must be unique integers — mitigation: assign IDs sequentially (1–30) and verify with `jq '[.panels[].id] | unique | length'`.
- **RISK-002**: `fastauth_auth_sessions_active` is only updated when sessions are created/revoked via the API; it won't reflect DB state if rows are inserted manually — mitigation: document this in the panel description.
- **ASSUMPTION-001**: Grafana provisioning folder path inside the container is `/etc/grafana/dashboards` (configurable in `dashboards.yml`).
- **ASSUMPTION-002**: The app is running and emitting metrics before Prometheus first scrapes; panels will show "No data" until the first scrape succeeds.

## 8. Architecture Diagram

```
┌─────────────┐   scrape /metrics    ┌────────────┐
│  fastauth   │ ──────────────────▶  │ Prometheus │
│  app:8000   │                      └─────┬──────┘
└─────────────┘                            │ PromQL queries
                                     ┌─────▼──────┐
                                     │  Grafana   │  ◀── provisioning/
                                     │ :3000      │      dashboards/
                                     └────────────┘      fastauth.json
```

## 9. Related Specs & Further Reading

- `conf/prometheus/prometheus.yml` — scrape config
- `conf/prometheus/alerts.yml` — alert rules referenced in annotations
- `app/core/metrics.py` — all metric definitions
- `compose.telemetry.yaml` — Grafana/Prometheus/Jaeger stack
- [Grafana dashboard provisioning docs](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards)
