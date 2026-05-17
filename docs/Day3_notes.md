# Day 3 — Foundation

**Goal:** Full Docker Compose skeleton running, database schema created, `/health` endpoint returning 200.

**Status: Complete**

---

## What Was Built

### Files Created

- `docker-compose.yml` — all 9 services defined and running
- `coordinator/app/core/config.py` — settings loaded from `.env`
- `coordinator/app/database.py` — async SQLAlchemy engine + session factory
- `coordinator/app/models.py` — all 6 database tables as SQLAlchemy models
- `coordinator/app/main.py` — FastAPI app with lifespan + `/health` endpoint
- `coordinator/Dockerfile` — Python 3.11 slim image
- `coordinator/requirements.txt` — all dependencies
- `monitoring/otel-collector-config.yml` — OTel pipeline config
- `monitoring/prometheus.yml` — Prometheus scrape config
- `.env` — environment variables (not committed)
- `.gitignore` — excludes `.env`, `__pycache__`, `*.pyc`

---

## Services Running

| Service        | Image                             | Port                           |
| -------------- | --------------------------------- | ------------------------------ |
| coordinator    | hermes-coordinator (custom build) | 8080 (host) → 8000 (container) |
| postgres       | postgres:15                       | internal only                  |
| kafka          | confluentinc/cp-kafka:7.5.0       | internal only                  |
| zookeeper      | confluentinc/cp-zookeeper:7.5.0   | internal only                  |
| otel-collector | otel/opentelemetry-collector      | internal only                  |
| jaeger         | jaegertracing/all-in-one          | 16686                          |
| prometheus     | prom/prometheus                   | 9090                           |
| grafana        | grafana/grafana                   | 3001                           |

---

## Database Tables Created

All 6 tables created automatically on coordinator startup via `Base.metadata.create_all`:

- `users` — JWT auth
- `workers` — registered worker instances
- `circuit_breaker_state` — per-worker CB state (CLOSED/OPEN/HALF_OPEN)
- `workflow_definitions` — workflow templates with steps as JSONB
- `workflow_executions` — individual execution instances
- `task_executions` — one row per step per execution, with idempotency key

---

## Health Endpoint

```
GET http://127.0.0.1:8080/health
```

Response:

```json
{
  "status": "ok",
  "database": "ok",
  "kafka": "ok",
  "version": "0.1.0"
}
```

---

## Issues Encountered & Fixed

**Port conflict on 8000**
Apache HTTP Server (`httpd.exe`) was already running on port 8000 with SSL. Fixed by mapping coordinator to host port 8080 in `docker-compose.yml`.

**otel-collector jaeger exporter removed**
Newer OTel collector versions removed the `jaeger` exporter. Fixed by switching to `otlp/jaeger` exporter pointing to `jaeger:4317`.

**Kafka health check timing out**
`confluent_kafka` AdminClient is a blocking call — running it in an async FastAPI endpoint caused timeouts. Resolved by verifying Kafka connectivity directly inside the container (`docker compose exec`), confirming the network works, and simplifying the health check.

**`/usr/bin/python3` not found**
Used on Windows — Linux path. Fixed by using `python` instead.

---

## Key Concepts Learned

**SQLAlchemy async engine** — `create_async_engine` with `postgresql+asyncpg://` driver. The `+asyncpg` part tells SQLAlchemy to use the async driver instead of the default blocking one.

**FastAPI lifespan** — replaces the old `@app.on_event("startup")` pattern. Everything before `yield` runs on startup, everything after on shutdown.

**Docker internal networking** — services communicate using their container names as hostnames (e.g. `kafka:29092`, `postgres:5432`). External access uses mapped host ports.

**Kafka internal vs external listeners** — `kafka:29092` is for internal Docker service-to-service communication. `localhost:9092` is for host machine access. The coordinator must use `kafka:29092`.

---

_Day 3 complete — Hermes build, May 2026._
