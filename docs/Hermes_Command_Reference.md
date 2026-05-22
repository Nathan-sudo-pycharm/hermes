# Hermes — Command Reference & Screenshot Guide

When I say a keyword in square brackets like `[RUN: SUBMIT-EXEC]`, find that keyword
in this doc and run the command listed under it.

---

## DOCKER COMMANDS

### [RUN: DOCKER-UP-ALL]

Start all services:

```powershell
docker compose up
```

### [RUN: DOCKER-UP-CORE]

Start only infrastructure (Kafka, Zookeeper, Postgres):

```powershell
docker compose up kafka zookeeper postgres
```

### [RUN: DOCKER-UP-APP]

Start coordinator + all workers:

```powershell
docker compose up coordinator worker-a worker-b worker-c
```

### [RUN: DOCKER-UP-FLAKY]

Start coordinator + worker-c only (for retry/failure testing):

```powershell
docker compose up coordinator worker-c
```

### [RUN: DOCKER-DOWN]

Stop and remove all containers:

```powershell
docker compose down
```

### [RUN: DOCKER-PS]

Check which containers are running and their status:

```powershell
docker compose ps
```

### [RUN: DOCKER-BUILD-ALL]

Rebuild coordinator and all workers:

```powershell
docker compose build coordinator worker-a worker-b worker-c
```

### [RUN: DOCKER-BUILD-COORD]

Rebuild only the coordinator:

```powershell
docker compose build coordinator
```

### [RUN: DOCKER-RESTART-WORKER-C]

Restart worker-c without rebuilding:

```powershell
docker compose restart worker-c
```

### [RUN: DOCKER-RECREATE-WORKER-C]

Force recreate worker-c (picks up docker-compose.yml env changes):

```powershell
docker compose up worker-c --force-recreate
```

### [RUN: LOGS-COORD]

View last 30 coordinator logs:

```powershell
docker compose logs coordinator --tail 30
```

### [RUN: LOGS-WORKER-C]

View last 20 worker-c logs:

```powershell
docker compose logs worker-c --tail 20
```

### [RUN: LOGS-WORKER-A]

View last 20 worker-a logs:

```powershell
docker compose logs worker-a --tail 20
```

---

## AUTH COMMANDS

### [RUN: REGISTER]

Register a new user (only needed once):

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/auth/register" -Method Post -ContentType "application/json" -Body '{"email":"nathan@hermes.dev","password":"hermes123"}'
```

### [RUN: LOGIN]

Get a fresh JWT token — run this at the start of every test session:

```powershell
$token = (Invoke-RestMethod -Uri "http://localhost:8080/auth/login" -Method Post -ContentType "application/json" -Body '{"email":"nathan@hermes.dev","password":"hermes123"}').access_token
```

### [RUN: CHECK-TOKEN]

Confirm token was captured:

```powershell
echo $token
```

---

## WORKFLOW COMMANDS

### [RUN: CREATE-DEFINITION]

Create a workflow definition (only needed once per session):

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/workflows/definitions" -Method Post -Headers @{Authorization="Bearer $token"} -ContentType "application/json" -Body '{"name":"test-workflow","steps":[{"name":"validate","timeout_seconds":10,"max_retries":3}]}'
```

**Note:** Save the `id` from the response — this is your `DEFINITION_ID`.

### [RUN: SUBMIT-EXEC]

Submit one workflow execution:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/workflows/execute" -Method Post -Headers @{Authorization="Bearer $token"} -ContentType "application/json" -Body '{"definition_id":"f2524b1b-6bb2-41c9-ae88-f5d20ae1a3e6","input_payload":{}}'
```

---

## DATABASE QUERIES

### [RUN: DB-TASKS]

View recent task executions with state and worker:

```powershell
docker compose exec postgres psql -U hermes -d hermes -c "SELECT id, step_name, state, attempt_number, worker_id, duration_ms FROM task_executions ORDER BY queued_at DESC LIMIT 10;"
```

### [RUN: DB-WORKFLOWS]

View recent workflow executions:

```powershell
docker compose exec postgres psql -U hermes -d hermes -c "SELECT id, state, completed_at, error_msg FROM workflow_executions ORDER BY started_at DESC LIMIT 5;"
```

### [RUN: DB-TASK-SUMMARY]

Count tasks grouped by worker and state:

```powershell
docker compose exec postgres psql -U hermes -d hermes -c "SELECT worker_id, state, COUNT(*) FROM task_executions GROUP BY worker_id, state ORDER BY worker_id;"
```

### [RUN: DB-DLQ]

View all dead-lettered tasks:

```powershell
docker compose exec postgres psql -U hermes -d hermes -c "SELECT id, step_name, attempt_number, error_msg FROM task_executions WHERE state = 'DEAD_LETTERED';"
```

### [RUN: DB-WORKERS]

View registered workers:

```powershell
docker compose exec postgres psql -U hermes -d hermes -c "SELECT id, grpc_address, last_heartbeat_at FROM workers;"
```

### [RUN: DB-CIRCUIT-BREAKER]

View circuit breaker states per worker:

```powershell
docker compose exec postgres psql -U hermes -d hermes -c "SELECT worker_id, state, failure_count, opened_at FROM circuit_breaker_state;"
```

---

## KAFKA COMMANDS

### [RUN: KAFKA-READ-TASKS]

Read all messages from hermes.tasks topic (from beginning):

```powershell
docker compose exec kafka kafka-console-consumer --topic hermes.tasks --bootstrap-server localhost:9092 --from-beginning
```

### [RUN: KAFKA-READ-DLQ]

Read all messages from the Dead Letter Queue topic:

```powershell
docker compose exec kafka kafka-console-consumer --topic hermes.tasks.dlq --bootstrap-server localhost:9092 --from-beginning
```

### [RUN: KAFKA-LIST-TOPICS]

List all Kafka topics:

```powershell
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

---

## PROTO / GRPC COMMANDS

### [RUN: PROTO-GENERATE]

Regenerate gRPC Python stubs from proto files:

```powershell
python -m grpc_tools.protoc -I coordinator/proto --python_out=coordinator/generated --grpc_python_out=coordinator/generated coordinator/proto/hermes.proto

python -m grpc_tools.protoc -I worker/proto --python_out=worker/generated --grpc_python_out=worker/generated worker/proto/hermes.proto
```

---

## FAILURE RATE CONTROL

### [RUN: FORCE-FAIL]

To force worker-c to always fail (for DLQ/retry testing):

1. Open `docker-compose.yml`
2. Change `WORKER_FAILURE_RATE: "0.4"` → `"1.0"` under worker-c
3. Run:

```powershell
docker compose up worker-c --force-recreate
```

### [RUN: RESTORE-FAIL-RATE]

To restore normal failure rate after testing:

1. Open `docker-compose.yml`
2. Change `WORKER_FAILURE_RATE: "1.0"` → `"0.4"` under worker-c
3. Run:

```powershell
docker compose up worker-c --force-recreate
```

---

## UI LINKS

| Tool             | URL                        | What it shows                |
| ---------------- | -------------------------- | ---------------------------- |
| Swagger API Docs | http://localhost:8080/docs | Interactive REST API testing |
| Grafana          | http://localhost:3001      | Metrics dashboards           |
| Jaeger           | http://localhost:16686     | Distributed traces           |
| Prometheus       | http://localhost:9090      | Raw metrics                  |

---

## SCREENSHOT CHECKLIST

Take these screenshots at the end of each day as documentation evidence.

### Every Day

- [ ] `[RUN: DOCKER-PS]` — all services running
- [ ] `[RUN: DB-TASK-SUMMARY]` — task state counts

### Day 5 (already done)

- [x] `docker compose logs worker-a` showing task received + SUCCESS
- [x] Kafka topic showing published task messages
- [x] `docker compose ps` all services healthy

### Day 6

- [ ] `docker compose logs coordinator` showing `gRPC server listening on port 50051`
- [ ] `docker compose logs worker-a` showing `ReportResult ack: received=True`
- [ ] `[RUN: DB-TASKS]` showing `state=SUCCESS`, `worker_id=worker-a`, `duration_ms` filled
- [ ] `[RUN: DB-WORKFLOWS]` showing `state=COMPLETED`

### Day 7

- [ ] `[RUN: DB-TASKS]` showing `FAILED (attempt 1)` → `FAILED (attempt 2)` → `DEAD_LETTERED (attempt 3)`
- [ ] `[RUN: DB-DLQ]` showing the dead-lettered task
- [ ] `[RUN: KAFKA-READ-DLQ]` showing the DLQ Kafka message
- [ ] `GET http://localhost:8080/dlq/tasks` response in Swagger UI

### Day 8 (Circuit Breaker — upcoming)

- [ ] `[RUN: DB-CIRCUIT-BREAKER]` showing state transitions: CLOSED → OPEN → HALF_OPEN → CLOSED
- [ ] `[RUN: LOGS-COORD]` showing circuit breaker state change logs

### Day 9 (Observability — upcoming)

- [ ] Jaeger UI showing a complete trace across coordinator + worker
- [ ] Grafana dashboard showing task execution metrics

### Day 11 (Dashboard — upcoming)

- [ ] Next.js dashboard running at localhost:3000
- [ ] Workflow list and execution status visible in UI

---

---

## Known Issues & TODOs

| ID      | Issue                                                                    | Affected Component                          | Fix Plan                                                      |
| ------- | ------------------------------------------------------------------------ | ------------------------------------------- | ------------------------------------------------------------- |
| TODO-01 | First heartbeat fails on worker startup — coordinator gRPC not ready yet | `worker/app/heartbeat.py`                   | Add `await asyncio.sleep(5)` before the first heartbeat fires |
| TODO-02 | `active_tasks` in heartbeat always reports 0                             | `worker/app/heartbeat.py`                   | Track in-flight task count in worker state                    |
| TODO-03 | HALF_OPEN does not limit to one probe task                               | `coordinator/app/circuit_breaker/engine.py` | Add a flag to block further tasks until probe result received |
| TODO-04 | Circuit breaker does not block Kafka task dispatch                       | `coordinator/app/grpc_server/handlers.py`   | Requires per-worker Kafka topics or a dispatch layer          |
| TODO-05 | Heartbeat interval hardcoded to 30s                                      | `worker/app/heartbeat.py`                   | Move to `settings.HEARTBEAT_INTERVAL` config value            |

---

_Keep this file open in a split editor tab while working on Hermes._
