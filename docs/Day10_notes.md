# Hermes Engineering Notes — 2026-05-23
**Session:** Day 10 — Prometheus Metrics + Grafana Dashboard
**Project:** Hermes — Distributed Workflow Orchestration Platform
**Engineer:** Nathan Ivor Sequeira

---

## 1. Goal of Today's Session

Add observability metrics to the Hermes platform so that:
- The coordinator exposes a `/metrics` endpoint in Prometheus format
- Custom metrics track task outcomes, durations, workflow counts, and circuit breaker states
- Prometheus scrapes the coordinator every 15 seconds
- Grafana auto-provisions a dashboard on startup showing live platform health

---

## 2. What We Built

### Files Created

| File | Purpose |
|---|---|
| `coordinator/app/core/metrics.py` | Defines all custom Prometheus metrics |
| `monitoring/grafana/provisioning/datasources/prometheus.yml` | Auto-provisions Prometheus as Grafana datasource |
| `monitoring/grafana/provisioning/dashboards/dashboard.yml` | Tells Grafana where to find dashboard JSON files |
| `monitoring/grafana/provisioning/dashboards/hermes.json` | Hermes Platform dashboard definition (5 panels) |

### Files Modified

| File | Change |
|---|---|
| `coordinator/requirements.txt` | Added `prometheus-client` |
| `coordinator/app/main.py` | Mounted `/metrics` ASGI endpoint |
| `coordinator/app/grpc_server/handlers.py` | Records task metrics and circuit breaker gauge on every ReportResult |
| `coordinator/app/routers/workflows.py` | Increments `workflow_executions_total` counter on each submission |

---

## 3. Engineering Reasoning

### What each file does

**`metrics.py` — metric definitions**

Defines four metrics using `prometheus-client`:

- `hermes_tasks_total` — a Counter with labels `worker_id` and `status`. Counters only go up. Every completed task increments this. Labels allow Prometheus to break it down by worker and by outcome (success, failed, dead_lettered).
- `hermes_task_duration_seconds` — a Histogram with custom buckets (0.1s to 10s) per worker. Histograms record distributions — from this, Prometheus can calculate p50, p95, p99 latencies.
- `hermes_workflow_executions_total` — a simple Counter incremented each time a workflow is submitted.
- `hermes_circuit_breaker_state` — a Gauge per worker. Gauges can go up and down. Maps states to numbers: CLOSED=0, OPEN=1, HALF_OPEN=2.

---

**`/metrics` endpoint in `main.py`**

```python
app.mount("/metrics", make_asgi_app())
```

`make_asgi_app()` from `prometheus-client` creates a standard ASGI app that serves all registered metrics in Prometheus text format. Mounting it at `/metrics` exposes it on the coordinator's HTTP server. Prometheus scrapes this URL every 15 seconds.

---

**`handlers.py` — metric recording**

After every `ReportResult`:
- `tasks_total.labels(worker_id=..., status="success").inc()` — increments success counter
- `tasks_total.labels(worker_id=..., status="failed").inc()` — increments failure counter
- `tasks_total.labels(worker_id=..., status="dead_lettered").inc()` — increments DLQ counter
- `task_duration_seconds.labels(worker_id=...).observe(ms / 1000)` — records duration in seconds
- Circuit breaker gauge updated after DB read

The reason metrics are recorded in the coordinator handler and not in the worker is that the coordinator is the single source of truth for task outcomes. The worker's view of success/failure is local — the coordinator's DB write is authoritative.

---

**Grafana provisioning**

The `docker-compose.yml` already mounted `./monitoring/grafana/provisioning:/etc/grafana/provisioning`. Creating files in that directory means Grafana automatically loads them on startup — no manual UI configuration needed.

Three files are needed:
1. `datasources/prometheus.yml` — registers Prometheus as a data source pointing at `http://prometheus:9090`
2. `dashboards/dashboard.yml` — tells Grafana to scan a folder for JSON dashboard files
3. `dashboards/hermes.json` — the actual dashboard with 5 panels

This is the correct production pattern: dashboards as code, not manually created through the UI (which would be lost on container restart).

---

### Why prometheus-client over opentelemetry metrics

Both OTel and `prometheus-client` can expose metrics. For Day 10 we use `prometheus-client` directly because:
- It is the native library for Prometheus — zero translation layer
- Simpler setup for custom business metrics (task counts, circuit breaker state)
- OTel metrics pipeline (via the OTel Collector) adds complexity without benefit at this scale

The OTel Collector config already has a Prometheus exporter on port 8889 for OTel-generated metrics — this is separate from the custom business metrics we're adding today.

---

### Why use Histogram for task duration instead of Gauge

A Gauge would only show the most recent task duration — not useful for understanding performance trends. A Histogram records every observation into buckets and lets Prometheus calculate percentile queries like:

```promql
histogram_quantile(0.95, rate(hermes_task_duration_seconds_bucket[1m]))
```

This returns the 95th percentile task duration over the last minute — a much more useful signal than a single current value.

---

## 4. Problems and Errors Encountered

### Problem 1 — `docker compose build --no-pull` flag not recognised

```
unknown flag: --no-pull
```

Same issue as Day 9. The installed Docker Compose version does not support this flag.

### Problem 2 — Grafana not loading

After running `docker compose build coordinator` and `docker compose up coordinator`, Grafana was not accessible at `localhost:3001`. Only the coordinator container was running.

### Problem 3 — Time series panels showed "No data" initially

Task Execution Rate and Task Duration p95 panels showed no data immediately after dashboard loaded.

---

## 5. Debugging Process

### Fix 1 — `--no-pull` flag

**Root cause:** Same as Day 9 — unsupported flag in this Docker Compose version.
**Fix:** `pull_policy: never` already in `docker-compose.yml`. Ran `docker compose build coordinator` without flags.

---

### Fix 2 — Grafana not loading

**Root cause:** `docker compose up coordinator` only starts the coordinator service. Grafana is a separate container.
**Fix:** Ran `docker compose up` to start all services.

---

### Fix 3 — Time series panels empty

**Root cause:** Prometheus `rate()` function requires at least two data points separated in time to calculate a rate. Immediately after startup there is only one scrape.
**Fix:** Submitted 3-5 executions and waited 2 minutes for Prometheus to accumulate scrape data. Panels then showed data.

---

## 6. Current Project Status

### Working

- `/metrics` endpoint live on coordinator ✅
- `hermes_tasks_total` counter recording by worker and status ✅
- `hermes_task_duration_seconds` histogram recording per worker ✅
- `hermes_workflow_executions_total` counter incrementing on submission ✅
- `hermes_circuit_breaker_state` gauge updating on ReportResult ✅
- Prometheus scraping coordinator every 15s ✅
- Grafana auto-provisioned with Prometheus datasource on startup ✅
- Hermes Platform dashboard with 5 panels deployed ✅
- Dashboard confirmed showing: 3 workflows, 3 tasks, circuit breaker=0 ✅

### Technical Debt / TODOs

| Item | Notes |
|---|---|
| Worker metrics not exposed | Workers have no `/metrics` endpoint — only coordinator metrics tracked |
| Retry count metric missing | No metric tracking how many retries occurred |
| Grafana dashboard not persisted in volume | Dashboard defined as code in JSON — correct approach, no issue |
| `circuit_breaker_state` gauge only updates on ReportResult | If no tasks run, stale gauge value persists — should also update on Heartbeat |
| No alerting rules configured | Prometheus alerts (e.g. circuit open > 60s) not set up |
