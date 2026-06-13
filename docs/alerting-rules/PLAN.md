---
goal: Fill out Prometheus alerting rules with real thresholds for all key signals
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: amjadjibon
status: 'Planned'
tags: [chore, architecture]
---

# Prometheus Alerting Rules

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

`conf/prometheus/alerts.yml` currently has two rules (high error rate, high p99 latency). This plan adds rules for brute-force blocks, MFA failures, active session anomalies, and registration spikes — covering all four concern areas the Grafana dashboard already visualises.

## 1. Requirements & Constraints

- **REQ-001**: Every alert must reference a metric already emitted by `app/core/metrics.py`; no new instrumentation.
- **REQ-002**: Each alert must have `severity` (`critical` / `warning`) and human-readable `summary` + `description` annotations.
- **CON-001**: Thresholds must be conservative enough to avoid alert fatigue in a lightly-loaded dev environment; use `for: 5m` guards unless a signal warrants immediate firing.
- **GUD-001**: Use `$__rate_interval` equivalent — `rate(...[5m])` is consistent with existing rules.
- **GUD-002**: Alert names must match the `ALERTS{alertname=~"Fastauth.*"}` annotation query wired in the Grafana dashboard.

## 2. Implementation Steps

> **Agent instructions**: This repo uses git. Use `git add -A && git commit -m "<message>"` at each phase boundary. Update checkboxes to `[x]` as each task is completed.

### Phase 1: Brute-Force and Auth Failure Alerts

**Goal**: Alert when brute-force blocks or login failure rates spike.

- [ ] TASK-001: Add `FastauthBruteForceBlocks` alert to `conf/prometheus/alerts.yml`: expr `rate(fastauth_auth_brute_force_blocks_total[5m]) > 0.1` (more than 1 block per ~10s), `for: 2m`, severity `warning`.
- [ ] TASK-002: Add `FastauthHighLoginFailureRate` alert: expr ratio of failed login attempts to total `> 0.3` (>30% failure rate) sustained for `5m`, severity `warning`. Metric: `fastauth_auth_login_attempts_total{success="false"}` / `fastauth_auth_login_attempts_total`.
- [ ] TASK-003: Add `FastauthMFAFailureSpike` alert: expr `rate(fastauth_auth_mfa_attempts_total{success="false"}[5m]) > 0.2`, `for: 5m`, severity `warning`.

**Completion criteria**: `docker compose -f compose.yaml -f compose.telemetry.yaml up -d prometheus` starts; `curl -s localhost:9090/api/v1/rules | jq '.data.groups[].rules[].name'` lists all three new alert names.

**git commit**: `git add -A && git commit -m "chore: add brute-force and auth failure alert rules"`

---

### Phase 2: Latency and Traffic Alerts

**Goal**: Cover p95 latency (the existing rule only covers p99) and sudden traffic drops (service down detection).

- [ ] TASK-004: Add `FastauthHighP95Latency` alert: expr `histogram_quantile(0.95, rate(fastauth_http_request_duration_seconds_bucket[5m])) > 1`, `for: 5m`, severity `warning` (p99 > 2s is already `critical`; p95 > 1s is an early warning).
- [ ] TASK-005: Add `FastauthNoTraffic` alert: expr `rate(fastauth_http_requests_total[5m]) == 0`, `for: 3m`, severity `critical` — catches the app being down or Prometheus losing the scrape target.

**Completion criteria**: Both new rule names appear in `curl localhost:9090/api/v1/rules`.

**git commit**: `git add -A && git commit -m "chore: add latency and no-traffic alert rules"`

---

### Phase 3: Registration Spike and Session Anomaly Alerts

**Goal**: Detect abuse patterns (registration flood, session count anomaly).

- [ ] TASK-006: Add `FastauthRegistrationSpike` alert: expr `rate(fastauth_auth_registrations_total[5m]) * 60 > 20` (>20 registrations/min), `for: 2m`, severity `warning`.
- [ ] TASK-007: Add `FastauthSessionCountHigh` alert: expr `fastauth_auth_sessions_active > 1000`, `for: 5m`, severity `warning` — adjust threshold to match expected production load.

**Completion criteria**: All 7 rules total appear in Prometheus; `conf/prometheus/alerts.yml` passes `promtool check rules conf/prometheus/alerts.yml` with exit 0.

**git commit**: `git add -A && git commit -m "chore: add registration spike and session anomaly alert rules"`

---

### Phase 4: Validate with promtool

**Goal**: Prove the YAML is syntactically correct and all expressions parse.

- [ ] TASK-008: Run `docker run --rm -v $(pwd)/conf/prometheus:/etc/prometheus prom/prometheus:latest promtool check rules /etc/prometheus/alerts.yml` — must exit 0.
- [ ] TASK-009: Update `conf/prometheus/alerts.yml` header comment listing all alert names and their purpose for operator reference.

**Completion criteria**: `promtool check rules` exits 0 with "SUCCESS" output.

**git commit**: `git add -A && git commit -m "chore: validate alert rules with promtool"`

---

## 3. Alternatives Considered

- **ALT-001**: Use Grafana alerting instead of Prometheus rules — rejected because Prometheus rules fire independently of Grafana availability and integrate with Alertmanager.
- **ALT-002**: Add Alertmanager routing config — out of scope for this plan; the rules are useful without a routing target.

## 4. Dependencies

- **DEP-001**: Prometheus running via `compose.telemetry.yaml` — already in place.
- **DEP-002**: All metrics referenced must be emitted by `app/core/metrics.py` — verified before writing rules.

## 5. Affected Files

- **FILE-001**: `conf/prometheus/alerts.yml` — add 7 new alert rules

## 6. Testing

- [ ] TEST-001: `docker run --rm -v $(pwd)/conf/prometheus:/etc/prometheus prom/prometheus:latest promtool check rules /etc/prometheus/alerts.yml` exits 0.
- [ ] TEST-002: Start stack, trigger 5 failed logins in a row, confirm `FastauthHighLoginFailureRate` transitions to `pending` in Prometheus UI at `localhost:9090/alerts`.

## 7. Risks & Assumptions

- **RISK-001**: `fastauth_auth_sessions_active` is only updated via API calls, not DB state — the session count alert may lag; document this in the alert description.
- **ASSUMPTION-001**: `fastauth_auth_login_attempts_total` has a `success` label with values `"true"` / `"false"` — verify in `app/core/metrics.py` before writing the ratio expression.

## 8. Architecture Diagram

```
app:8000/metrics  ──scrape──▶  Prometheus
                                    │
                              alerts.yml rules
                                    │
                         ┌──────────┴──────────┐
                         │  ALERTS{}  series   │
                         └──────────┬──────────┘
                                    │
                              Grafana annotations
                              (red lines on panels)
```

## 9. Related Specs & Further Reading

- `conf/prometheus/alerts.yml` — existing rules (2)
- `app/core/metrics.py` — all metric definitions
- `docs/grafana-dashboard/PLAN.md` — dashboard annotation query `ALERTS{alertname=~"Fastauth.*"}`
