# Hermes Engineering Notes — Day 5
**Session:** Day 5 — Kafka Producer + Worker Consumer + Task Execution
**Project:** Hermes — Distributed Workflow Orchestration Platform
**Engineer:** Nathan Ivor Sequeira

> Note: These notes were reconstructed from session logs and code review.

---

## 1. Goal of Today's Session

Connect the coordinator to the worker via Kafka so that:
- Submitting a workflow execution via REST API publishes a task message to Kafka
- A worker consumes the message from the Kafka topic
- The worker executes the task (simulated) and logs the result
- The full flow from API call to worker execution is verified end-to-end

This was the first time the coordinator and worker communicated — through Kafka rather than directly.

---

## 2. What We Built

### Files Created

| File | Purpose |
|---|---|
| `coordinator/app/kafka/producer.py` | Kafka producer — publishes task messages to `hermes.tasks` |
| `worker/app/kafka/consumer.py` | Kafka consumer — subscribes to `hermes.tasks`, receives tasks |
| `worker/app/executor/task_runner.py` | Task runner — simulates task execution, logs result |
| `worker/app/core/config.py` | Worker config — WORKER_ID, failure rate, task duration, Kafka settings |

### Files Modified

| File | Change |
|---|---|
| `coordinator/app/routers/workflows.py` | `execute_workflow` endpoint now publishes task to Kafka after creating DB rows |
| `worker/app/main.py` | Starts Kafka consumer as background asyncio task on startup |
| `docker-compose.yml` | Added worker-a, worker-b, worker-c services with distinct environment configs |

---

## 3. Engineering Reasoning

### What each file does

**`coordinator/app/kafka/producer.py`**

Creates a single global `confluent_kafka.Producer` instance (lazy initialisation on first use). The producer is thread-safe so one instance serves the entire coordinator process.

`publish_task()` takes a task message dict, serialises it to JSON, and produces it to the `hermes.tasks` topic. The message key is `task_execution_id` — this ensures all retry attempts for the same task land on the same Kafka partition, preserving order.

`delivery_report()` is a callback fired by the Kafka client when a message is confirmed delivered or fails. It logs the outcome but does not raise exceptions — failures are logged and monitored separately.

---

**`worker/app/kafka/consumer.py`**

Creates a `confluent_kafka.Consumer` with a shared group ID `hermes-workers`. This means all worker instances share the same consumer group — Kafka distributes partitions across them automatically.

The consumer runs in an infinite `while True` loop inside an asyncio coroutine. It uses `loop.run_in_executor` to call the blocking `consumer.poll()` without blocking the event loop. On receiving a valid message, it deserialises the JSON and calls `run_task()`.

The outer loop handles connection errors — if Kafka goes down, the consumer waits 5 seconds and reconnects instead of crashing the process.

---

**`worker/app/executor/task_runner.py`**

Simulates task execution:
- Logs task start with worker ID and step name
- Sleeps for `WORKER_TASK_DURATION` seconds (configurable per worker)
- Randomly fails based on `WORKER_FAILURE_RATE` (configurable per worker)
- Logs SUCCESS or FAILED

At this stage, the result is only logged. The `# gRPC result reporting will be added on Day 6` comment marks where the actual reporting logic will go.

---

### The Kafka message schema

Every task message published to `hermes.tasks` contains:

```json
{
  "task_execution_id": "uuid",
  "execution_id": "uuid",
  "step_name": "validate",
  "step_index": 0,
  "idempotency_key": "{execution_id}:{step_index}:{attempt_number}",
  "timeout_seconds": 10,
  "max_retries": 3,
  "attempt_number": 1,
  "input_payload": {},
  "traceparent": null
}
```

`idempotency_key` is the most important field. Its format — `"{execution_id}:{step_index}:{attempt_number}"` — makes each attempt uniquely identifiable. On Day 7 this prevents the same task being executed twice if reassigned.

`traceparent` is set to null here. The placeholder is already in the schema so Day 9 OTel tracing can inject it without changing the message format.

---

### Why three workers with different configs

| Worker | Failure Rate | Task Duration | Purpose |
|---|---|---|---|
| worker-a | 0% | 0.3s | Fast baseline — always succeeds |
| worker-b | 0% | 4.0s | Slow baseline — always succeeds but takes time |
| worker-c | 40% | 1.5s | Flaky — used to test retry, DLQ, circuit breaker |

Three distinct worker personalities allow testing different failure scenarios without changing code. The failure rate and duration are environment variables, not hardcoded.

---

### Why asyncio + run_in_executor for Kafka polling

`confluent_kafka`'s `poll()` is a blocking call. Calling it directly inside an async function would freeze the entire event loop — the FastAPI health endpoint, heartbeat loop, and everything else would stop responding.

`loop.run_in_executor(None, lambda: consumer.poll(timeout=1.0))` runs the blocking poll in a thread pool while yielding control back to the asyncio event loop. This keeps the worker fully responsive while waiting for Kafka messages.

---

## 4. Problems and Errors Encountered

### Problem 1 — Workers not receiving tasks initially
After starting all services, no task messages appeared in worker logs despite the coordinator returning 201.

### Problem 2 — Kafka consumer group rebalancing delay
On first startup, workers took several seconds before starting to consume — the consumer group rebalance was not instant.

### Problem 3 — `auto.offset.reset: earliest` caused old messages to replay
When restarting workers after testing, they consumed messages from the beginning of the topic including stale test messages from earlier runs.

---

## 5. Debugging Process

### Fix 1 — Workers not receiving tasks

**Root cause:** Kafka partition assignment. With one partition on `hermes.tasks` and three consumers in the same group, only one worker gets the partition. The others wait idle. Worker-a was assigned the partition on first startup.

**Investigation:** Ran `docker compose logs worker-a` and saw `subscribed to hermes.tasks` and task received logs. Workers b and c showed subscribed but no received messages.

**Lesson:** In a single-partition topic, only one consumer in a group is ever active. To distribute load across workers, the topic needs multiple partitions (one per worker). For this project, single-partition is acceptable since we are not optimising for throughput.

---

### Fix 2 — Rebalance delay

**Root cause:** Kafka's group coordinator waits for `group.initial.rebalance.delay.ms` before assigning partitions. Configured to 0 in docker-compose to minimise this.

**Fix:** `KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0` was already in the Kafka container config.

---

### Fix 3 — Stale message replay

**Root cause:** `auto.offset.reset: earliest` tells the consumer to start from the beginning of the topic when no committed offset exists. After a restart with no committed offsets, all previous messages replay.

**Context:** This is expected and acceptable behaviour for a learning system. In production, `auto.offset.reset: latest` would be used after initial setup.

---

## 6. Current Project Status (End of Day 5)

### Working
- `POST /workflows/execute` publishes task to `hermes.tasks` ✅
- Worker subscribes to `hermes.tasks` on startup ✅
- Worker receives and deserialises task message ✅
- `task_runner.py` simulates execution and logs result ✅
- Three workers running with distinct configurations ✅
- Kafka message schema includes `task_execution_id`, `idempotency_key`, `traceparent` placeholder ✅
- Verified via `kafka-console-consumer` showing correctly structured messages ✅

### Incomplete at End of Day 5
- Task result not reported back to coordinator (gRPC — Day 6)
- `task_executions` DB row state stuck at QUEUED — never updated
- `workflow_executions` state stuck at RUNNING — never completed
- `task_runner.py` has stub comments where gRPC calls will go

---

*End of Day 5 Engineering Notes*
