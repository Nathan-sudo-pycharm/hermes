# Hermes Engineering Notes — 2026-05-22

**Session:** Day 9 — Distributed Tracing with OpenTelemetry
**Engineer:** Nathan Ivor Sequeira

---

## 1. Goal of Today's Session

Wire OpenTelemetry distributed tracing through the full workflow execution path so that:

- Every HTTP request to the coordinator produces a trace
- The trace context (traceparent) travels through Kafka to the worker
- The worker creates a child span linked to the coordinator's trace
- The full execution path is visible in Jaeger UI as one connected trace

---

## 2. What We Built

### Files Created

| File                                | Purpose                                   |
| ----------------------------------- | ----------------------------------------- |
| `coordinator/app/core/telemetry.py` | OTel tracer setup for coordinator service |
| `worker/app/core/telemetry.py`      | OTel tracer setup for worker service      |

### Files Modified

| File                                   | Change                                                                                    |
| -------------------------------------- | ----------------------------------------------------------------------------------------- |
| `coordinator/app/routers/workflows.py` | Creates `execute_workflow` span, injects traceparent into Kafka message                   |
| `worker/app/executor/task_runner.py`   | Extracts traceparent from Kafka message, creates child `run_task` span with attributes    |
| `coordinator/app/main.py`              | Calls `setup_telemetry()` at module level, instruments FastAPI with `FastAPIInstrumentor` |
| `worker/app/main.py`                   | Calls `setup_telemetry()` at module level                                                 |

---

## 3. Engineering Reasoning

### What each file does

**`coordinator/app/core/telemetry.py`**

Sets up the OpenTelemetry tracer provider for the coordinator. Three things happen here:

1. A `Resource` is created with `service.name = "hermes-coordinator"` — this is how Jaeger labels the service in the UI
2. An `OTLPSpanExporter` is created pointing at `otel-collector:4317` — the OTel Collector container running in Docker
3. A `BatchSpanProcessor` wraps the exporter — it batches spans before sending to reduce network overhead

`get_tracer()` returns a named tracer that any module can use to create spans.

---

**`worker/app/core/telemetry.py`**

Identical to coordinator's setup except `service.name = "hermes-worker"`. This is what causes the yellow badge in Jaeger to be labelled separately from the coordinator spans.

---

**`coordinator/app/routers/workflows.py` — traceparent injection**

After creating the workflow execution and task rows, the `execute_workflow` endpoint now:

1. Gets a tracer via `get_tracer()`
2. Opens a span called `execute_workflow`
3. Sets attributes: `workflow.execution_id`, `workflow.definition`, `task.step_name`
4. Calls `inject(carrier)` — this writes the current trace context into a plain dict as `{"traceparent": "00-<trace_id>-<span_id>-01"}`
5. That traceparent string is placed into the Kafka message under the `"traceparent"` key

The `"traceparent": None` placeholder that was already in the Kafka message from Day 5 was designed for exactly this purpose.

---

**`worker/app/executor/task_runner.py` — traceparent extraction**

When the worker receives a Kafka message, `run_task()` now:

1. Reads `task.get("traceparent")` from the message
2. Calls `extract({"traceparent": traceparent_string})` — this reconstructs the trace context
3. Opens a span called `run_task` with that context as parent — this is what links the worker span to the coordinator's trace
4. Sets attributes: `task.execution_id`, `task.step_name`, `worker.id`, `task.success`

Without step 3, the worker span would appear as a separate disconnected trace in Jaeger. With it, the span is a child of `execute_workflow` in the same trace.

---

**`coordinator/app/main.py` — FastAPI instrumentation**

`setup_telemetry()` is called at module level (before the app is created). After the app is created, `FastAPIInstrumentor.instrument_app(app)` is called. This auto-creates spans for every HTTP request without any manual code in the route handlers — it's why the `POST /workflows/execute http receive` and `http send` spans appear automatically in the waterfall.

---

### Why OTel Collector is used instead of exporting directly to Jaeger

The worker and coordinator export spans to the OTel Collector at `otel-collector:4317`. The collector then forwards to Jaeger. This indirection means:

- Services only know about the collector, not about Jaeger specifically
- The collector can be reconfigured to forward to a different backend (Tempo, Zipkin, cloud observability) without touching service code
- The collector handles batching, retry, and compression between services and the backend

The `otel-collector-config.yml` was already configured correctly for this from Day 3.

---

### How traceparent propagates through Kafka

Kafka has no built-in concept of headers in our current setup (we use JSON message values). The W3C traceparent string is embedded in the message payload:

```json
{
  "task_execution_id": "...",
  "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
}
```

The worker reads it as a plain string from the dict and passes it to `extract()`. This is a manual propagation pattern — simpler than Kafka header propagation and appropriate for a learning project.

---

## 4. Problems and Errors Encountered

### Problem 1 — Docker build TLS handshake timeout

```
net/http: TLS handshake timeout
failed to resolve source metadata for docker.io/library/python:3.11-slim
```

Docker tried to pull the latest `python:3.11-slim` base image from Docker Hub and timed out due to a network issue.

### Problem 2 — `--no-pull` flag not recognised

```
unknown flag: --no-pull
```

The installed Docker Compose version does not support `--no-pull`.

---

## 5. Debugging Process

### Fix 1 — Docker Hub TLS timeout

**Root cause:** Docker Compose attempts to verify the base image against the registry on every build even when the image is cached locally.

**Fix:** Added `pull_policy: never` to each service in `docker-compose.yml`. This instructs Docker Compose to never pull base images from the registry and always use what is cached locally.

**Lesson:** For local development on restricted or intermittent networks, always set `pull_policy: never` on services that use cached base images. Only remove this for CI/CD where fresh base images are needed.

---

### Fix 2 — `--no-pull` not supported

**Root cause:** Docker Compose version installed does not support the `--no-pull` flag (it was removed or renamed in some versions).

**Fix:** Used `pull_policy: never` in `docker-compose.yml` as a persistent alternative that works regardless of the CLI flag support.

---

## 6. Current Project Status

### Working

- Full distributed trace across coordinator and worker in one Jaeger timeline ✅
- `hermes-coordinator` and `hermes-worker` appear as separate service nodes in Jaeger ✅
- `execute_workflow` span with workflow attributes (execution_id, definition name, step name) ✅
- `run_task` span with task attributes (execution_id, step name, worker ID, success flag) ✅
- FastAPI auto-instrumentation creates HTTP spans for every route ✅
- traceparent propagates through Kafka message payload ✅
- OTel Collector receives spans and forwards to Jaeger correctly ✅
- 6 traces confirmed in Jaeger UI with both service badges ✅

### Technical Debt / TODOs

| Item                                       | Notes                                                                                |
| ------------------------------------------ | ------------------------------------------------------------------------------------ |
| gRPC spans not traced                      | ReportResult gRPC calls are not instrumented — no span for the result reporting path |
| Retry tasks do not carry traceparent       | Retry rows created in handlers.py do not copy the traceparent from the original task |
| Worker heartbeat spans not traced          | Heartbeat gRPC calls produce no spans                                                |
| Kafka consumer span not created            | No span wraps the message consumption step on the worker side                        |
| `pull_policy: never` in docker-compose.yml | Must be removed or overridden in CI/CD to ensure fresh base images                   |
