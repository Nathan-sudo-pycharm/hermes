# Hermes Engineering Notes — 2026-05-27

**Session:** Day 12 — Load Testing + Health Hardening
**Engineer:** Nathan Ivor Sequeira

---

## 1. Goal of Today's Session

- Prove the system handles concurrent load without failure
- Harden the `/health` endpoint to check both DB and Kafka
- Add a `/ready` readiness probe for container orchestrators
- Identify and fix bugs exposed by load testing
- Document performance characteristics for portfolio and university application

---

## 2. What We Built

### Files Created

| File            | Purpose                                                        |
| --------------- | -------------------------------------------------------------- |
| `locustfile.py` | Load test script — 4 task types simulating real user behaviour |

### Files Modified

| File                                   | Change                                                                                                            |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `coordinator/app/main.py`              | Replaced single DB-only `/health` with Kafka+DB check; added `/ready` probe; moved Kafka check to thread executor |
| `coordinator/app/routers/workflows.py` | Added `selectinload` to `list_executions` and `execute_workflow` to fix MissingGreenlet error                     |

---

## 3. Engineering Reasoning

### What each file does

**`locustfile.py` — load test definition**

Defines a `HermesUser` class with four weighted tasks:

- `submit_execution` (weight 3) — most frequent. Submits a workflow execution. This is the core write path: coordinator → Kafka → worker → gRPC → DB. Tests the full system under write pressure.
- `list_executions` (weight 2) — reads all workflow executions. Tests DB read performance under concurrent access.
- `check_health` (weight 1) — hits `/health`. Verifies the health endpoint stays fast under load.
- `list_workers` (weight 1) — hits `/workers/`. Tests the circuit breaker state read path.

`on_start()` runs once per virtual user at spawn time — logs in and stores the JWT token. All subsequent requests use that token in the Authorization header.

`wait_time = between(1, 3)` — each user waits 1-3 seconds between tasks, simulating realistic human pacing rather than hammering as fast as possible.

---

**`/health` endpoint — hardened**

The original `/health` only checked PostgreSQL. If Kafka went down, `/health` would still return `status: ok` — a false positive that would prevent operators from noticing a critical dependency failure.

The hardened version checks both:

1. PostgreSQL — `SELECT 1` query via async SQLAlchemy
2. Kafka — `AdminClient.list_topics()` via confluent_kafka

The Kafka check uses `AdminClient` which is synchronous (blocking). Running it directly in an async FastAPI handler would freeze the entire event loop — blocking all other requests while waiting for the Kafka broker response. The fix: `loop.run_in_executor(None, _kafka_check)` runs the blocking call in a thread pool, yielding control back to the event loop while waiting.

The shared `_kafka_check()` function is defined once and reused by both `/health` and `/ready` — avoids duplication.

---

**`/ready` endpoint — readiness probe**

Separates two distinct concepts:

- **Liveness** (`/health`): Is the process running? Even a degraded service should return something here. Returning 200 with `status: degraded` keeps the container alive while alerting operators.
- **Readiness** (`/ready`): Can this service handle traffic right now? Returns 503 if ANY dependency is down. Container orchestrators (Kubernetes, ECS) use this to stop routing traffic to an instance that can't serve requests.

Returns `{"ready": true}` with 200 on full health, or `{"ready": false, "database": false, "kafka": false}` with 503 on any failure.

---

**`selectinload` fix in workflows.py**

`WorkflowExecutionResponse` has a `tasks: List[TaskExecutionResponse]` field added in a previous session. This requires SQLAlchemy to load the `tasks` relationship before Pydantic serialises the response.

Without `selectinload`, SQLAlchemy uses lazy loading — it tries to issue a SELECT query when Pydantic accesses `execution.tasks`. In an async context, this triggers `MissingGreenlet` because there is no active async database session at serialisation time.

`selectinload` is an eager loading strategy — it loads all related tasks in a second SQL query immediately after the main query, within the same async session. By the time Pydantic serialises the object, the data is already in memory.

Three endpoints needed this fix:

- `execute_workflow` — reloads the execution with selectinload before returning
- `list_executions` — loads all executions with their tasks in one operation
- `get_execution` — already had this fix from a previous session

---

### Why Locust over other load testing tools

- **Python-based** — no new language. The script is readable and modifiable without learning JMeter XML or k6 JavaScript.
- **Web UI** — live charts and statistics without needing external dashboards.
- **Weighted tasks** — models realistic user behaviour (more writes than reads, occasional health checks).
- **Per-user state** — each virtual user maintains its own JWT token, matching how real API clients behave.

---

## 4. Problems and Errors Encountered

### Problem 1 — urllib3 import error on Locust startup

```
ImportError: cannot import name 'create_urllib3_context' from 'urllib3.util'
```

### Problem 2 — 66% failure rate on first load test run

`/workflows/execute` and `/workflows/executions` both showed 100% failure rates despite auth working fine.

### Problem 3 — Blocking Kafka AdminClient freezing event loop

`/health` 95th percentile response time was 17-29 seconds. All other endpoints timed out as a result.

### Problem 4 — Two `/health` endpoints defined in main.py

The old health endpoint was not removed before adding the new one. FastAPI silently used the first definition.

### Problem 5 — 500 Internal Server Error on authenticated endpoints

```
fastapi.exceptions.ResponseValidationError
MissingGreenlet: greenlet_spawn has not been called
loc: ('response', 'tasks')
```

---

## 5. Debugging Process

### Fix 1 — urllib3 import error

**Root cause:** Version conflict between installed urllib3 and the version Locust expected.

**Fix:**

```powershell
pip install --upgrade urllib3 locust
```

---

### Fix 2 — High failure rate (first run)

**Root cause:** The blocking `AdminClient.list_topics()` in the `/health` endpoint was freezing the asyncio event loop for up to 17 seconds per call. With 20 users hitting `/health` repeatedly, the event loop was constantly blocked, causing all other requests (`/workflows/execute`, `/workflows/executions`) to time out and fail.

**Fix:** Moved the Kafka check into a thread executor:

```python
loop = asyncio.get_event_loop()
await loop.run_in_executor(None, _kafka_check)
```

**Lesson:** Never run blocking I/O directly in an async FastAPI handler. Always use `run_in_executor` for synchronous library calls.

---

### Fix 3 — Duplicate `/health` endpoint

**Root cause:** The old health endpoint was left in `main.py` when the new one was added.

**Investigation:** Spotted by reviewing the pasted `main.py` content — two `@app.get("/health")` decorators visible.

**Fix:** Removed the old endpoint, kept only the hardened version.

**Lesson:** When replacing a route, always delete the old one. FastAPI uses the first matching route silently — duplicate routes produce no error but wrong behaviour.

---

### Fix 4 — MissingGreenlet 500 error

**Root cause:** `WorkflowExecutionResponse` schema includes `tasks: List[TaskExecutionResponse]`. This requires the SQLAlchemy relationship to be loaded before serialisation. `list_executions` and `execute_workflow` used plain `select(WorkflowExecution)` without `selectinload` — triggering lazy loading during Pydantic serialisation, which fails in async context.

**Investigation:** Error traceback in coordinator logs clearly identified:

- `loc: ('response', 'tasks')` — serialisation failing on tasks field
- `MissingGreenlet` — lazy loading attempted outside async session

**Fix:** Added `.options(selectinload(WorkflowExecution.tasks))` to both `list_executions` and `execute_workflow`. For `execute_workflow`, a fresh query with selectinload is issued before returning the response.

**Lesson:** In async SQLAlchemy, all relationship fields used in Pydantic responses must be eagerly loaded. Lazy loading is not supported in async context.

---

## 6. Load Test Results (Final Clean Run)

**Configuration:** 20 concurrent users, spawn rate 2/s, 90 second duration

| Endpoint                  | Requests | Failures | Median   | p95       | RPS      |
| ------------------------- | -------- | -------- | -------- | --------- | -------- |
| POST /auth/login          | 20       | 0        | 520ms    | 1000ms    | —        |
| GET /health               | 86       | 0        | 71ms     | 150ms     | 1.5      |
| GET /workers              | 69       | 0        | 9ms      | 130ms     | 1.5      |
| POST /workflows/execute   | 247      | 0        | 64ms     | 720ms     | 4.5      |
| GET /workflows/executions | 156      | 0        | 78ms     | 470ms     | 2.6      |
| **Aggregated**            | **578**  | **0**    | **66ms** | **650ms** | **10.1** |

**Summary:**

- 0% failure rate under 20 concurrent users ✅
- 9.18 RPS sustained throughput
- 64ms median response on the core write path (workflow execution)
- 720ms p95 on workflow execution — well within acceptable range
- Health endpoint responding in 71ms median — fast and non-blocking ✅

---

## 7. Current Project Status

### Working

- Load test: 578 requests, 0 failures, 9.18 RPS under 20 users ✅
- `/health` checks both PostgreSQL and Kafka ✅
- `/ready` returns 503 when dependencies are down ✅
- Kafka health check runs in thread executor — non-blocking ✅
- `selectinload` on all endpoints returning WorkflowExecution with tasks ✅
- `locustfile.py` committed to repo for reproducible load testing ✅

### Technical Debt / TODOs

| Item                                     | Notes                                                     |
| ---------------------------------------- | --------------------------------------------------------- |
| No pagination on `/workflows/executions` | Returns all rows — will degrade with large datasets       |
| DB connection pool not tuned             | Default pool size may bottleneck under higher load        |
| Load test uses hardcoded definition ID   | Should be dynamic — create definition in on_start         |
| No load test for gRPC endpoints          | Only REST API tested — gRPC ReportResult not covered      |
| No sustained load test                   | 90 seconds is short — longer runs may reveal memory leaks |

---

_End of Day 12 Notes_
