# Hermes

> _Messages delivered. Failures contained. Nothing lost._

---

There are systems that run tasks.  
And then there are systems that know what to do when things go wrong.

**Hermes** is a self-hosted distributed workflow orchestration platform — built for engineers who've been burned by silent failures, duplicate executions, and cascading outages.

It doesn't just run your workflows. It watches them. It isolates failing workers before they can take anything else down. It retries with patience. And when something truly cannot be recovered, it remembers — so you don't lose the story of what happened.

---

## Who it's for

Teams and engineers who run multi-step automated work across services and need it to be **observable**, **fault-tolerant**, and **honest about failure**.

---

## What's under the hood

| Layer                  | Technology               |
| ---------------------- | ------------------------ |
| API + Coordinator      | Python, FastAPI          |
| Task Queue             | Apache Kafka + Zookeeper |
| Internal Communication | gRPC                     |
| Database               | PostgreSQL               |
| Distributed Tracing    | OpenTelemetry + Jaeger   |
| Metrics                | Prometheus + Grafana     |
| Containerisation       | Docker Compose           |

---

## Architecture

```
Client
  │
  ▼
Coordinator (FastAPI + gRPC server)
  │  publishes task
  ▼
Kafka (hermes.tasks topic)
  │  consumed by
  ▼
Worker (A / B / C)
  │  reports result via gRPC
  ▼
Coordinator
  │  updates
  ▼
PostgreSQL
```

Every execution produces a distributed trace visible in Jaeger.  
Every task outcome is recorded as a Prometheus metric visible in Grafana.

---

## Core Features

### Kafka-backed Task Execution

Workflows are submitted via REST API. The coordinator publishes each task step to a Kafka topic. Workers consume and execute independently. No direct coupling between coordinator and worker.

### gRPC Result Reporting

Workers report task outcomes (success, failure, duration) back to the coordinator via gRPC. The coordinator updates the database and transitions workflow state accordingly.

### Retry with Exponential Backoff

Failed tasks are retried automatically up to `max_attempts`. Each retry is scheduled with exponential backoff:

```
delay = min(2 ^ attempt_number, 30) seconds
```

Each attempt is tracked as a separate database row with its own idempotency key — preventing double execution.

### Dead Letter Queue

Tasks that exhaust all retry attempts are marked `DEAD_LETTERED` and published to `hermes.tasks.dlq`. The coordinator exposes a `GET /dlq/tasks` endpoint to inspect them.

### Circuit Breaker State Machine

Each worker has an independent circuit breaker tracked by the coordinator:

```
CLOSED → (3 failures) → OPEN → (30s timeout) → HALF_OPEN → (probe success) → CLOSED
```

Prevents the system from repeatedly sending tasks to a broken worker.

### Distributed Tracing

Every workflow execution generates an OpenTelemetry trace. The trace context travels from the coordinator through Kafka to the worker — both services appear as linked spans in Jaeger.

### Prometheus Metrics + Grafana Dashboard

The coordinator exposes `/metrics` with:

- `hermes_tasks_total` — task completions by worker and status
- `hermes_task_duration_seconds` — execution duration histogram per worker
- `hermes_workflow_executions_total` — total workflows submitted
- `hermes_circuit_breaker_state` — live circuit breaker state per worker (0=CLOSED, 1=OPEN, 2=HALF_OPEN)

A Grafana dashboard is auto-provisioned on startup.

### Worker Heartbeats

Workers send periodic heartbeats to the coordinator via gRPC. The coordinator uses heartbeats to update worker health records and trigger circuit breaker timeout transitions.

---

## Services

| Service     | Port  | Description                    |
| ----------- | ----- | ------------------------------ |
| Coordinator | 8080  | REST API + gRPC server         |
| Worker A    | 8001  | Fast worker, 0% failure rate   |
| Worker B    | 8002  | Slow worker, 0% failure rate   |
| Worker C    | 8003  | Flaky worker, 40% failure rate |
| PostgreSQL  | 5432  | Primary database               |
| Kafka       | 9092  | Task message queue             |
| Jaeger UI   | 16686 | Distributed trace viewer       |
| Prometheus  | 9090  | Metrics storage                |
| Grafana     | 3001  | Metrics dashboard              |

---

## Getting Started

**Prerequisites:** Docker Desktop, Docker Compose

```bash
git clone https://github.com/Nathan-sudo-pycharm/hermes.git
cd hermes
docker compose up
```

API available at `http://localhost:8080/docs`  
Grafana at `http://localhost:3001` (admin / admin)  
Jaeger at `http://localhost:16686`

---

## API Overview

| Method | Endpoint                     | Description                             |
| ------ | ---------------------------- | --------------------------------------- |
| POST   | `/auth/register`             | Register a user                         |
| POST   | `/auth/login`                | Get JWT token                           |
| POST   | `/workflows/definitions`     | Create a workflow definition            |
| GET    | `/workflows/definitions`     | List all definitions                    |
| POST   | `/workflows/execute`         | Submit a workflow execution             |
| GET    | `/workflows/executions`      | List all executions                     |
| GET    | `/workflows/executions/{id}` | Get execution by ID                     |
| GET    | `/workers/`                  | List workers with circuit breaker state |
| GET    | `/dlq/tasks`                 | List dead-lettered tasks                |
| GET    | `/health`                    | Coordinator health check                |
| GET    | `/metrics`                   | Prometheus metrics                      |

---

## Project Structure

```
hermes/
├── coordinator/          # FastAPI coordinator service
│   ├── app/
│   │   ├── circuit_breaker/  # Circuit breaker state machine
│   │   ├── core/             # Config, telemetry, metrics
│   │   ├── grpc_server/      # gRPC server + handlers
│   │   ├── kafka/            # Kafka producer
│   │   ├── retry/            # Retry scheduler
│   │   ├── routers/          # REST API routes
│   │   └── models.py         # SQLAlchemy models
│   ├── generated/            # gRPC generated stubs
│   └── proto/                # Protobuf definition
├── worker/               # Worker service
│   ├── app/
│   │   ├── core/             # Config, telemetry
│   │   ├── executor/         # Task runner
│   │   ├── grpc_client/      # gRPC client
│   │   └── kafka/            # Kafka consumer
│   ├── generated/            # gRPC generated stubs
│   └── proto/                # Protobuf definition
├── proto/                # Source of truth proto file
├── monitoring/           # Prometheus, Grafana, OTel config
├── docs/                 # Engineering notes per day
└── docker-compose.yml
```

---

## Engineering Documentation

Session-by-session build notes are in `docs/`:

| Day    | Topic                                                                      |
| ------ | -------------------------------------------------------------------------- |
| Day 3  | Foundation — PostgreSQL schema, Docker Compose, health endpoint            |
| Day 4  | Authentication — JWT, user registration and login                          |
| Day 5  | Kafka — coordinator producer, worker consumer, task execution              |
| Day 6  | gRPC — ReportResult, database updates, workflow state transitions          |
| Day 7  | Retry — exponential backoff, dead letter queue                             |
| Day 8  | Circuit Breaker — CLOSED/OPEN/HALF_OPEN state machine, worker heartbeats   |
| Day 9  | Tracing — OpenTelemetry, Jaeger, cross-service trace propagation via Kafka |
| Day 10 | Metrics — Prometheus custom metrics, Grafana dashboard auto-provisioning   |

---

## Status

`[ in progress ]` — built in the open, documented honestly, limitations included.

---

_Named after the Greek messenger god.  
He delivered everything. He lost nothing._
