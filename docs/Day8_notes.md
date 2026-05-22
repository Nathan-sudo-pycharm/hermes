**Session:** Day 8 — Circuit Breaker State Machine + Worker Heartbeats
**Project:** Hermes — Distributed Workflow Orchestration Platform
**Engineer:** Nathan Ivor Sequeira

---

## 1. Goal of Today's Session

Implement a circuit breaker per worker that:

- Tracks failure counts from gRPC ReportResult calls
- Opens the circuit after 3 consecutive failures (stops trusting that worker)
- Waits 30 seconds then moves to HALF_OPEN (allows one probe task)
- Closes the circuit if the probe succeeds, reopens if it fails
- Workers send periodic heartbeats so the coordinator knows they are alive
- REST endpoint exposes live circuit breaker state per worker

---

## 2. What We Built

### Files Created

| File                                          | Purpose                                                    |
| --------------------------------------------- | ---------------------------------------------------------- |
| `coordinator/app/circuit_breaker/__init__.py` | Package marker                                             |
| `coordinator/app/circuit_breaker/engine.py`   | Circuit breaker state machine logic                        |
| `coordinator/app/routers/workers.py`          | REST endpoint — GET /workers with circuit breaker status   |
| `worker/app/heartbeat.py`                     | Background loop — sends heartbeat to coordinator every 30s |

### Files Modified

| File                                      | Change                                                                                                                                       |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `coordinator/app/grpc_server/handlers.py` | Calls `record_failure` / `record_success` after every ReportResult. Heartbeat handler now upserts worker record and calls `check_transition` |
| `coordinator/app/main.py`                 | Registered workers router                                                                                                                    |
| `worker/app/grpc_client/client.py`        | Added `send_heartbeat()` function                                                                                                            |
| `worker/app/main.py`                      | Starts heartbeat loop as asyncio background task alongside Kafka consumer                                                                    |

---

## 3. Engineering Reasoning

### What each file does

**`engine.py` — the state machine**

Contains three functions:

- `record_failure(session, worker_id)` — increments failure count. If count reaches threshold (3) and state is CLOSED → transitions to OPEN, sets `opened_at` and `next_retry_at`. If state is HALF_OPEN and a failure occurs → goes back to OPEN (probe failed).
- `record_success(session, worker_id)` — if state is HALF_OPEN → transitions to CLOSED, resets failure count to 0. If state is CLOSED → resets failure count.
- `check_transition(session, worker_id)` — called on every Heartbeat. If state is OPEN and `next_retry_at` has passed → transitions to HALF_OPEN. This is how the timeout-based recovery works.
  A helper `_get_or_create()` ensures a circuit breaker row always exists for a worker before any state logic runs.

---

**`handlers.py` — updated ReportResult and Heartbeat**

ReportResult now calls `record_failure` or `record_success` after updating the task row. This is the correct place because the coordinator only knows a worker failed when the worker reports it via gRPC.

Heartbeat now does two things:

1. Upserts the worker row in the `workers` table (updates `last_heartbeat_at`)
2. Calls `check_transition` to check if an OPEN circuit should move to HALF_OPEN
   The transition happens on Heartbeat rather than on a timer because: the heartbeat is a natural clock signal from the worker itself. If a worker is dead, no heartbeat arrives, and the circuit stays OPEN — which is correct behaviour.

---

**`workers.py` — REST endpoint**

`GET /workers` joins the `workers` table with `circuit_breaker_state` and returns per-worker status including: `last_heartbeat_at`, circuit state, failure count, and when it opened/will retry.

---

**`heartbeat.py` — worker-side loop**

Runs as an asyncio background task. Every 30 seconds calls `send_heartbeat()` via gRPC. Sends `worker_id`, `state="idle"`, and `active_tasks=0`. In a future version this would send the real active task count.

---

**`client.py` — send_heartbeat added**

Added `send_heartbeat()` alongside the existing `report_result()`. Opens a gRPC channel to `COORDINATOR_GRPC_ADDRESS`, calls `Heartbeat` RPC, returns whether the coordinator accepted it.

---

### Why the HALF_OPEN transition is triggered by Heartbeat

The OPEN → HALF_OPEN transition needs a trigger. Two options:

- A separate background scheduler on the coordinator polls for OPEN circuits every N seconds
- The Heartbeat from the worker acts as the trigger
  Using Heartbeat is cleaner: it means the coordinator only considers recovery when the worker is provably alive and actively communicating. A scheduler could trigger HALF_OPEN for a worker that has crashed and gone silent — which would be wrong.

### Why failure_count is not decremented on each success (only reset on HALF_OPEN→CLOSED)

Partial credit for successes would make the circuit hard to reason about. The circuit only resets fully when the system has made a deliberate decision: the circuit was OPEN, a timeout passed, one probe was allowed, and it succeeded. That is a controlled recovery — not gradual forgiveness.

### Why static worker seeding is kept alongside heartbeat upsert

If workers start slightly after the coordinator, the first task they process could arrive before their first heartbeat. The static seed ensures the FK constraint on `task_executions.worker_id` is always satisfiable at startup. Heartbeat upsert then keeps the record fresh. The seed is a safety net, not the source of truth.

---

## 4. Problems and Errors Encountered

### Problem 1 — Worker-a consuming all tasks, worker-c never triggered

Kafka assigns one partition to one consumer in a group. Worker-a connected first and held the partition. Worker-c received no tasks, so the circuit breaker was never exercised.

### Problem 2 — Needed 12 failures to confirm OPEN state

The test ran more executions than the threshold of 3. `failure_count` reached 12 before the DB was checked. This is expected — once OPEN, the circuit stays OPEN regardless of further failures coming in. The state was correct.

---

## 5. Debugging Process

### Fix 1 — Force worker-c to receive tasks

**Root cause:** Kafka partition ownership. Worker-a owned the only partition.

**Fix:** `docker compose stop worker-a worker-b` to remove them from the consumer group. Kafka rebalanced and assigned the partition to worker-c.

---

### Fix 2 — Force failures reliably

**Root cause:** 40% failure rate is random — not reliable for deterministic testing.

**Fix:** Used the existing debug endpoint:

```powershell
Invoke-RestMethod -Uri "http://localhost:8003/debug/failure-rate" -Method Post -ContentType "application/json" -Body '{"rate":1.0}'
```

Set to 1.0 to guarantee failures. Reset to 0.0 before probe test.

---

### Full circuit breaker cycle verified

| Step                           | State     | How triggered                            |
| ------------------------------ | --------- | ---------------------------------------- |
| Start                          | CLOSED    | Default                                  |
| 3+ failures reported           | OPEN      | `record_failure` in ReportResult handler |
| 30s passes + heartbeat arrives | HALF_OPEN | `check_transition` in Heartbeat handler  |
| Probe task succeeds            | CLOSED    | `record_success` in ReportResult handler |

---

## 6. Current Project Status

### Working

- Circuit breaker state machine: CLOSED → OPEN → HALF_OPEN → CLOSED ✅
- Failure threshold: opens at 3 failures ✅
- Timeout recovery: OPEN → HALF_OPEN after 30s via heartbeat ✅
- Probe recovery: HALF_OPEN → CLOSED on success ✅
- Worker heartbeats every 30s, coordinator upserts last_heartbeat_at ✅
- GET /workers returns live circuit breaker status per worker ✅
- All previous functionality (retry, DLQ, gRPC result reporting) intact ✅

### Technical Debt / TODOs

| Item                                         | Notes                                                                                                                                                      |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Circuit breaker does not block task dispatch | State is tracked and visible but Kafka still delivers tasks to OPEN workers. True enforcement requires per-worker topics or a dispatch layer. Future work. |
| `active_tasks` in heartbeat is always 0      | Worker does not track in-flight task count yet                                                                                                             |
| HALF_OPEN does not limit to one probe task   | Multiple tasks could arrive during HALF_OPEN window if Kafka delivers them quickly                                                                         |
| Heartbeat interval hardcoded to 30s          | Should be a config setting                                                                                                                                 |
| No alerting on OPEN state                    | A real system would page on circuit open                                                                                                                   |

---

_End of Day 8 Notes_
