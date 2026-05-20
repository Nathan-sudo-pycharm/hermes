# Hermes Engineering Notes — 2026-05-20

**Session:** Day 6 — Worker Task Execution + gRPC ReportResult + Database Update
**Project:** Hermes — Distributed Workflow Orchestration Platform
**Engineer:** Nathan Ivor Sequeira

---

## 1. Goal of Today's Session

Day 6 objective: close the execution loop that was left open at the end of Day 5.

At the end of Day 5, the system could:

- Accept a workflow execution via REST API
- Publish a task to Kafka
- Have a worker consume and execute the task
- Log SUCCESS or FAILED to stdout

What it could NOT do:

- Report the task outcome back to the Coordinator
- Update the `task_executions` table in PostgreSQL
- Transition the `workflow_executions` state to COMPLETED or FAILED

Day 6 was entirely about wiring that return path using gRPC.

Planned deliverables:

- `proto/hermes.proto` — gRPC contract file (source of truth)
- Generated Python stubs for both Coordinator and Worker
- `coordinator/app/grpc_server/handlers.py` — ReportResult handler with DB writes
- `coordinator/app/grpc_server/server.py` — gRPC server startup
- `worker/app/grpc_client/client.py` — gRPC client stub
- Updated `worker/app/executor/task_runner.py` — calls gRPC after execution
- Updated `coordinator/app/main.py` — starts gRPC server in lifespan

---

## 2. What We Built

### Files Created

| File                                       | Purpose                                  |
| ------------------------------------------ | ---------------------------------------- |
| `proto/hermes.proto`                       | Single source of truth for gRPC contract |
| `coordinator/proto/hermes.proto`           | Local copy for coordinator Docker build  |
| `worker/proto/hermes.proto`                | Local copy for worker Docker build       |
| `coordinator/generated/hermes_pb2.py`      | Auto-generated message classes           |
| `coordinator/generated/hermes_pb2_grpc.py` | Auto-generated gRPC service stubs        |
| `worker/generated/hermes_pb2.py`           | Auto-generated message classes           |
| `worker/generated/hermes_pb2_grpc.py`      | Auto-generated gRPC service stubs        |
| `coordinator/app/grpc_server/__init__.py`  | Package marker                           |
| `coordinator/app/grpc_server/handlers.py`  | ReportResult + Heartbeat handlers        |
| `coordinator/app/grpc_server/server.py`    | gRPC server setup on port 50051          |
| `worker/app/grpc_client/__init__.py`       | Package marker                           |
| `worker/app/grpc_client/client.py`         | gRPC client, calls ReportResult          |

### Files Modified

| File                                 | Change                                                 |
| ------------------------------------ | ------------------------------------------------------ |
| `coordinator/app/main.py`            | Added gRPC server startup + worker seeding to lifespan |
| `worker/app/executor/task_runner.py` | Added gRPC ReportResult call after task execution      |

### Infrastructure Changes

- `proto/`, `coordinator/proto/`, `worker/proto/` directories created
- `coordinator/generated/`, `worker/generated/` directories created
- gRPC stubs generated using `grpc_tools.protoc` locally

---

## 3. Engineering Reasoning

### Why gRPC for result reporting (not Kafka or REST)

The Worker needs to report a task result back to the Coordinator. Three options existed:

- **REST callback**: Simple but adds HTTP overhead and requires the Worker to know the Coordinator's REST address. No typed contract.
- **Kafka results topic** (`hermes.results`): Decoupled but asynchronous — the Coordinator has to poll a topic. Adds latency to DB updates and complexity to the consumer side.
- **gRPC**: Typed contract enforced by `.proto`. Both services are controlled, so the overhead of code generation is acceptable. Synchronous call means the Coordinator confirms receipt immediately. ADR-002 documents this decision formally.

gRPC was chosen. The `.proto` file is the authoritative interface — both sides must match it.

### Why proto files are duplicated per service

Each service (coordinator, worker) builds independently in Docker. A Docker build context is scoped to its own directory — `coordinator/Dockerfile` cannot reach `../../proto/`. Each service needs a local copy of the `.proto` to generate its stubs at build time or include pre-generated stubs. The root `proto/` is the master — never edit the copies directly.

### Why `sys.path.insert` for generated imports

The generated gRPC files (`hermes_pb2.py`, `hermes_pb2_grpc.py`) use a direct cross-import: `hermes_pb2_grpc.py` imports `hermes_pb2` by name, not by package path. If both files are placed in a Python package (with `__init__.py`), the cross-import breaks. The correct approach is to add the `generated/` directory itself to `sys.path` so both files are importable as top-level modules. This is done dynamically using `os.path` relative to the calling file, so it works in both Docker (`/app/generated`) and local development.

### Why `grpc.aio` (async) instead of synchronous gRPC

FastAPI and the worker both run on asyncio. The standard `grpc` library uses threads and does not integrate cleanly with asyncio event loops. `grpc.aio` is the official async gRPC library — it runs in the same event loop as FastAPI, avoiding thread management and blocking calls. Both the coordinator's gRPC server and the worker's gRPC client use `grpc.aio`.

### Why worker seeding in coordinator lifespan

The `task_executions.worker_id` column is a foreign key referencing the `workers` table. When a worker calls ReportResult, the handler sets `worker_id = "worker-a"`. PostgreSQL rejects this if `worker-a` does not exist in `workers`. The three workers are statically known from docker-compose, so they are seeded on coordinator startup. The seed function checks before inserting to avoid duplicate key errors on restart. On Day 8, worker registration will move to the Heartbeat handler (upsert on heartbeat), which is more dynamic and production-appropriate.

### Why workflow state logic is kept simple on Day 6

The current logic in `handlers.py` is:

- All tasks SUCCESS → workflow COMPLETED
- Any task FAILED → workflow FAILED
- Otherwise → RUNNING

This is intentionally incomplete. Day 7 adds retry logic — a FAILED task is not immediately terminal if `attempt_number < max_attempts`. The Day 6 handler will be extended on Day 7 to check attempt counts before closing the workflow.

---

## 4. Problems and Errors Encountered

### Problem 1 — `grep` not available in PowerShell

**Command attempted:**

```
find . -type f | grep -v __pycache__ | grep -v .git | ...
```

**Error:**

```
grep : The term 'grep' is not recognized as the name of a cmdlet...
```

### Problem 2 — Directories created with typo `porto` instead of `proto`

Files created:

```
proto/hermes.porto       ← wrong extension
coordinator/porto/       ← wrong directory name
worker/porto/            ← wrong directory name
```

### Problem 3 — `protoc` fails because `generated/` directories did not exist

**Error:**

```
coordinator/generated/: No such file or directory
worker/generated/: No such file or directory
```

### Problem 4 — Foreign key violation on first successful gRPC call

**Error (from coordinator logs):**

```
asyncpg.exceptions.ForeignKeyViolationError: insert or update on table
"task_executions" violates foreign key constraint "task_executions_worker_id_fkey"
DETAIL: Key (worker_id)=(worker-a) is not present in table "workers".
```

Full error surfaced in the worker log as a gRPC `StatusCode.UNKNOWN` because the coordinator's handler raised an unhandled exception.

### Problem 5 — Login failed with placeholder credentials

```
{"detail":"Invalid email or password"}
```

The test command used literal placeholder text `your@email.com` instead of real credentials.

---

## 5. Debugging Process

### Fix 1 — PowerShell file tree command

**Root cause:** `grep` is a Unix tool. PowerShell has no native `grep`.

**Fix:** Used PowerShell equivalent:

```powershell
Get-ChildItem -Recurse -File | Where-Object {
  $_.FullName -notmatch '__pycache__|\.git|node_modules|generated|\.pyc'
} | Select-Object -ExpandProperty FullName | Sort-Object
```

**Lesson:** Always check the shell environment before running Unix commands. Windows PowerShell requires different tooling.

---

### Fix 2 — Typo in directory and file names

**Root cause:** Typed `porto` instead of `proto` during directory and file creation.

**Fix:** PowerShell `Rename-Item`:

```powershell
Rename-Item proto\hermes.porto proto\hermes.proto
Rename-Item coordinator\porto coordinator\proto
Rename-Item worker\porto worker\proto
# repeated for all three directories
```

**Lesson:** Verify directory and file names immediately after creation, especially for names that look similar.

---

### Fix 3 — protoc `No such file or directory`

**Root cause:** `grpc_tools.protoc` does not create output directories automatically. They must exist before running the generator.

**Fix:**

```powershell
mkdir coordinator\generated
mkdir worker\generated
```

Then re-ran the generate commands.

**Lesson:** `protoc` is not forgiving — all output paths must exist before generation. This is a standard protoc behaviour, not a bug.

---

### Fix 4 — Foreign key violation: `worker-a` not in `workers` table

**Root cause:** The `task_executions` table has `worker_id` as a foreign key referencing `workers.id`. The handler was setting `task.worker_id = "worker-a"` before `worker-a` existed in the `workers` table. PostgreSQL enforced referential integrity and rejected the UPDATE.

**Investigation:** The full error was visible in the coordinator log (surfaced via gRPC error propagation to the worker log as `StatusCode.UNKNOWN`). The SQL statement and parameters were clearly shown, pointing directly at the FK constraint.

**Fix:** Added `seed_workers()` to the coordinator lifespan in `main.py`:

```python
async def seed_workers():
    known_workers = [
        {"id": "worker-a", "grpc_address": "worker-a:50052"},
        {"id": "worker-b", "grpc_address": "worker-b:50052"},
        {"id": "worker-c", "grpc_address": "worker-c:50052"},
    ]
    async with AsyncSessionLocal() as session:
        for w in known_workers:
            existing = await session.execute(
                select(Worker).where(Worker.id == w["id"])
            )
            if not existing.scalar_one_or_none():
                session.add(Worker(...))
        await session.commit()
```

**Lesson:** When a handler modifies a row with a foreign key column, all referenced rows must exist first. Always think about FK dependencies before writing handler logic. This class of error is silent until runtime — it doesn't appear during development until the FK is actually used.

---

### Fix 5 — Login with placeholder credentials

**Root cause:** The test command contained literal placeholder text copied without modification.

**Fix:** Registered a fresh test user:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/auth/register" \
  -Method Post -ContentType "application/json" \
  -Body '{"email":"nathan@hermes.dev","password":"hermes123"}'
```

**Lesson:** Always substitute placeholder values before running commands. Keep a note of test credentials used during development.

---

## 6. Current Project Status

### Working

- Full execution loop: REST → Kafka → Worker → gRPC → DB ✅
- `task_executions` updated with state, worker_id, duration_ms, completed_at ✅
- `workflow_executions` transitions to COMPLETED or FAILED ✅
- gRPC server starts on port 50051 alongside FastAPI ✅
- Worker seeds in `workers` table on coordinator startup ✅
- All 10 Docker services healthy ✅
- DB verified via direct SQL query ✅

### Incomplete / Technical Debt

| Item                                              | Notes                                                                                                                                                              |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Heartbeat handler is a stub                       | Logs only, no DB update. Proper upsert on Day 8.                                                                                                                   |
| Worker seeding is static                          | Hardcoded to 3 workers. Should move to dynamic registration via Heartbeat on Day 8.                                                                                |
| Failed tasks close the workflow immediately       | No retry logic yet. Day 7 replaces this.                                                                                                                           |
| Old task rows stuck in QUEUED state               | Rows from Day 5 test runs were never updated — they predate gRPC reporting. Not a bug, but DB is noisy.                                                            |
| `grpc_address` field on `workers` table is unused | Set to `"worker-x:50052"` as placeholder. Workers are gRPC clients in this architecture, not servers. This field may be repurposed or removed in a later refactor. |
| `/metrics` endpoint returns 404                   | Prometheus is trying to scrape the coordinator. OTel instrumentation not yet wired (Day 9).                                                                        |
| `generated/` folders not gitignored               | Generated files are currently committed to the build context. A `.gitignore` entry and Dockerfile generation step should be added before Day 13 CI work.           |

---

_End of Day 6 Notes_
