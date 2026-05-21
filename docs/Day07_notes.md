# Hermes Engineering Notes — 2026-05-21

**Session:** Day 7 — Retry Logic + Exponential Backoff + Dead Letter Queue  
**Project:** Hermes — Distributed Workflow Orchestration Platform  
**Engineer:** Nathan Ivor Sequeira

---

## 1. Goal of Today's Session

Extend the result-reporting pipeline built on Day 6 with:

- Retry logic on task failure (up to `max_attempts`)
- Exponential backoff between retry attempts
- Dead Letter Queue (DLQ) for tasks that exhaust all retries
- Background retry scheduler that re-publishes tasks to Kafka when backoff expires
- REST endpoint to inspect dead-lettered tasks

---

## 2. What We Built

### Files Created

| File                                 | Purpose                                                       |
| ------------------------------------ | ------------------------------------------------------------- |
| `coordinator/app/retry/__init__.py`  | Package marker                                                |
| `coordinator/app/retry/scheduler.py` | Background loop — polls DB, re-publishes due retries to Kafka |
| `coordinator/app/routers/dlq.py`     | REST endpoint — GET /dlq/tasks lists DEAD_LETTERED tasks      |

### Files Modified

| File                                      | Change                                                                    |
| ----------------------------------------- | ------------------------------------------------------------------------- |
| `coordinator/app/kafka/producer.py`       | Added optional `topic` parameter to `publish_task()`                      |
| `coordinator/app/grpc_server/handlers.py` | Replaced simple FAILED path with full retry state machine                 |
| `coordinator/app/main.py`                 | Started retry scheduler as asyncio background task, registered DLQ router |

---

## 3. Engineering Reasoning

### Why each failed task creates a NEW row instead of updating the existing one

The `idempotency_key` field is UNIQUE and follows the format `"{execution_id}:{step_index}:{attempt_number}"`. Each attempt has a different attempt number, so each attempt needs a different key — and therefore a different row. Keeping old rows as FAILED preserves full execution history. The new row (RETRYING → QUEUED) represents the next attempt cleanly.

### Why a background scheduler instead of sleeping in the handler

The gRPC handler must return quickly. Sleeping inside it would block other RPCs from being processed during the backoff period. The correct pattern: handler writes the retry row with `next_retry_at` and returns immediately. A separate asyncio task (the scheduler) polls every 2 seconds and re-publishes tasks whose backoff has expired. This keeps the handler fast and non-blocking.

### Why `asyncio.create_task()` for the scheduler

The scheduler runs forever in the background alongside FastAPI and the gRPC server — all sharing the same asyncio event loop. `create_task()` launches it as a concurrent coroutine without blocking startup. On shutdown, `scheduler_task.cancel()` stops it cleanly.

### Backoff formula

```
delay = min(2 ^ attempt_number, 30) seconds
```

| Attempt         | Delay |
| --------------- | ----- |
| 1 (first retry) | 2s    |
| 2               | 4s    |
| 3               | 8s    |
| Max cap         | 30s   |

### Why the DLQ is a Kafka topic AND a DB state

When a task is dead-lettered, two things happen:

1. `task_executions.state` is set to `DEAD_LETTERED` in PostgreSQL
2. A message is published to `hermes.tasks.dlq` Kafka topic

The DB state allows the REST API (`GET /dlq/tasks`) to query dead-lettered tasks without consuming from Kafka. The Kafka topic provides a durable, replayable audit log — useful for external alerting or reprocessing later.

---

## 4. Problems and Errors Encountered

### Problem 1 — Worker-c not picking up Kafka tasks

Worker-c started before Kafka's internal listener (port 29092) was fully ready. The consumer got `Connection refused` and stopped polling.

### Problem 2 — Token expiry during testing

JWT tokens expired multiple times during the testing session, causing `401 Unauthorized` and `Could not validate credentials` errors mid-test.

### Problem 3 — Coordinator and worker-c started without Kafka/Zookeeper

Running `docker compose up coordinator worker-c` without first ensuring Kafka was running caused worker-c to fail at Kafka connection on startup.

### Problem 4 — 40% failure rate did not trigger failures during testing

Worker-c's random failure simulation did not produce a failure during several consecutive test runs, making it impossible to observe retry behaviour naturally.

---

## 5. Debugging Process

### Fix 1 — Worker-c Kafka connection refused

**Root cause:** Kafka container was running but its internal listener (29092) was still initialising when worker-c started.

**Fix:** `docker compose restart worker-c` after Kafka was confirmed healthy. The consumer's built-in retry loop reconnected successfully on restart.

**Lesson:** Worker startup order matters. In production, use health checks or retry-with-backoff logic at the consumer connection level (already partially handled by our `while True` retry loop in `consumer.py`).

---

### Fix 2 — Token expiry

**Root cause:** JWT tokens have a short expiry configured in the coordinator. A new token must be obtained per session.

**Fix:** Re-run the login command before each test block.

**Lesson:** Store the token refresh as a one-liner and run it at the start of every test session. Documented in the command reference sheet.

---

### Fix 3 — Services started without dependencies

**Root cause:** `docker compose up coordinator worker-c` only starts the named services. Kafka, Zookeeper, and Postgres must already be running (or included in the command) for the coordinator and workers to function.

**Fix:** Always run `docker compose ps` first to verify infrastructure services are up before starting application services.

---

### Fix 4 — Forcing failures for testing

**Root cause:** 40% failure rate is random — statistically, several consecutive successes are expected.

**Fix:** Temporarily set `WORKER_FAILURE_RATE=1.0` in docker-compose.yml and recreate worker-c with `--force-recreate`. This guarantees every task fails, triggering the full retry chain and eventually DEAD_LETTERED state.

**Lesson:** Always have a way to force failure states during testing. Random failure rates are realistic but impractical for deterministic verification.

---

## 6. Current Project Status

### Working

- Full retry chain: FAILED → RETRYING → re-queued → FAILED → DEAD_LETTERED ✅
- Exponential backoff delay stored as `next_retry_at` in DB ✅
- Retry scheduler re-publishes tasks to Kafka when backoff expires ✅
- DLQ: dead-lettered tasks published to `hermes.tasks.dlq` Kafka topic ✅
- `GET /dlq/tasks` REST endpoint returns dead-lettered tasks ✅
- Workflow stays RUNNING while retries are in-flight ✅
- Workflow transitions to FAILED only after retries exhausted ✅

### Technical Debt / TODOs

| Item                                                          | Notes                                                                    |
| ------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Heartbeat handler is still a stub                             | Logs only, no DB upsert — Day 8                                          |
| Worker seeding is static                                      | Hardcoded 3 workers — Day 8 replaces with dynamic Heartbeat registration |
| `timeout_seconds` hardcoded to 10 in scheduler                | Should read from the task definition step config                         |
| No task timeout enforcement                                   | Worker can run indefinitely — timeout logic not yet implemented          |
| `WORKER_FAILURE_RATE` must be manually reset after testing    | Easy to forget — could cause all tasks to fail in next session           |
| Coordinator handler logs not visible in `docker compose logs` | Application log level not configured for handler modules — low priority  |

---

_End of Day 7 Engineering Notes_
