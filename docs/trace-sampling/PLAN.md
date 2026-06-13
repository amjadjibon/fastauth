---
goal: Configure OTEL trace sampling so Jaeger receives a representative subset rather than 100% of spans
version: 1.0
date_created: 2026-06-14
last_updated: 2026-06-14
owner: amjadjibon
status: 'Planned'
tags: [chore, architecture]
---

# Jaeger Trace Sampling Configuration

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

`app/core/telemetry.py` creates a `TracerProvider` with `BatchSpanProcessor` but no sampler — which defaults to `ALWAYS_ON` (100% sampling). Under load this produces excessive data and can slow the app. This plan adds configurable head-based sampling with a sensible default (10%) and a parent-based option that respects upstream decisions.

## 1. Requirements & Constraints

- **REQ-001**: Sampling rate must be configurable via env var without code changes.
- **REQ-002**: Default to 10% (`OTEL_SAMPLING_RATIO=0.1`) — sufficient for debugging while reducing Jaeger storage ~10×.
- **CON-001**: Do not break the existing `otel_enabled=false` path — when OTEL is off, no sampling code runs.
- **GUD-001**: Use `ParentBasedTraceIdRatio` sampler so distributed traces are consistent: if an upstream service samples a trace, all downstream spans in that trace are included.

## 2. Implementation Steps

> **Agent instructions**: This repo uses git. Use `git add -A && git commit -m "<message>"` at each phase boundary. Update checkboxes to `[x]` as each task is completed.

### Phase 1: Add Sampling Config

**Goal**: Expose `otel_sampling_ratio` in settings and wire it into the tracer provider.

- [ ] TASK-001: Add `otel_sampling_ratio: float = 0.1` to `Settings` in `app/core/config.py`. Validate range `0.0–1.0` with a `field_validator`.
- [ ] TASK-002: In `app/core/telemetry.py`, import `ParentBasedTraceIdRatio, TraceIdRatioBased` from `opentelemetry.sdk.trace.sampling`. Replace the bare `TracerProvider(resource=resource)` with `TracerProvider(resource=resource, sampler=ParentBasedTraceIdRatio(settings.otel_sampling_ratio))`.
- [ ] TASK-003: Add `OTEL_SAMPLING_RATIO=0.1` to `.env.example` with a comment explaining the range.
- [ ] TASK-004: Add `OTEL_SAMPLING_RATIO=1.0` to `.env.ci` so CI captures all traces (low traffic, useful for debugging CI failures).

**Completion criteria**: `uv run python -c "from app.core.telemetry import setup_telemetry; print('ok')"` runs without error. `Settings(secret_key='x', database_url='sqlite:///x').otel_sampling_ratio == 0.1`.

**git commit**: `git add -A && git commit -m "feat: add configurable OTEL trace sampling with ParentBasedTraceIdRatio"`

---

### Phase 2: Compose and Documentation

**Goal**: Expose the env var in the telemetry compose override and document the tradeoffs.

- [ ] TASK-005: Add `OTEL_SAMPLING_RATIO: ${OTEL_SAMPLING_RATIO:-0.1}` to the `app` service environment block in `compose.telemetry.yaml`.
- [ ] TASK-006: Add a comment block above the `otel_sampling_ratio` field in `app/core/config.py` explaining: `1.0` = all spans, `0.0` = no spans, `0.1` = 10% (recommended for production).

**Completion criteria**: `docker compose -f compose.yaml -f compose.telemetry.yaml config` renders the env var in the app service without errors.

**git commit**: `git add -A && git commit -m "chore: expose OTEL_SAMPLING_RATIO in compose and document sampling tradeoffs"`

---

## 3. Alternatives Considered

- **ALT-001**: Tail-based sampling (sample based on trace outcome, e.g. keep all errors) — rejected because it requires a Collector with the `tail_sampling` processor, which adds operational complexity; can be added later as a Collector pipeline.
- **ALT-002**: `TraceIdRatioBased` without `ParentBased` wrapper — rejected because it breaks distributed traces: some spans from the same trace would be dropped while others are kept.

## 4. Dependencies

- **DEP-001**: `opentelemetry-sdk` — already installed (used in `telemetry.py`).
- **DEP-002**: Jaeger running via `compose.telemetry.yaml` — already in place.

## 5. Affected Files

- **FILE-001**: `app/core/config.py` — add `otel_sampling_ratio` field
- **FILE-002**: `app/core/telemetry.py` — pass sampler to `TracerProvider`
- **FILE-003**: `.env.example` — document new env var
- **FILE-004**: `.env.ci` — set `OTEL_SAMPLING_RATIO=1.0` for CI
- **FILE-005**: `compose.telemetry.yaml` — pass env var to app service

## 6. Testing

- [ ] TEST-001: Set `OTEL_ENABLED=true OTEL_EXPORTER=console OTEL_SAMPLING_RATIO=0.0 uv run uvicorn main:app` and send 20 requests to `/livez` — no spans should appear in console output.
- [ ] TEST-002: Set `OTEL_SAMPLING_RATIO=1.0` and send 5 requests — all 5 should produce spans.
- [ ] TEST-003: `Settings(secret_key='x', database_url='sqlite:///x', otel_sampling_ratio=1.5)` should raise a `ValidationError`.

## 7. Risks & Assumptions

- **RISK-001**: `ParentBasedTraceIdRatio` is only meaningful if callers send `traceparent` headers; otherwise it falls back to the ratio sampler — this is the correct default behaviour.
- **ASSUMPTION-001**: `opentelemetry-sdk` version already installed exports `ParentBasedTraceIdRatio` from `opentelemetry.sdk.trace.sampling` — verify with `python -c "from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio"`.

## 8. Architecture Diagram

```
Incoming request
      │
      ▼
FastAPIInstrumentor
      │
      ▼
ParentBasedTraceIdRatio(ratio)
  ├── parent sampled?  ──yes──▶  RECORD_AND_SAMPLE
  └── no parent         ──▶  TraceIdRatioBased(ratio)
                                ├── sampled  ──▶  BatchSpanProcessor ──▶ Jaeger
                                └── dropped  ──▶  (discarded)
```

## 9. Related Specs & Further Reading

- `app/core/telemetry.py` — current tracer setup
- `app/core/config.py` — settings
- `compose.telemetry.yaml` — Jaeger + OTEL collector stack
- [OpenTelemetry Python sampling docs](https://opentelemetry.io/docs/languages/python/instrumentation/#sampling)
