# Hermes

[![Hermes CI](https://github.com/Nathan-sudo-pycharm/hermes/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Nathan-sudo-pycharm/hermes/actions/workflows/ci.yml)

> _Messages delivered. Failures contained. Nothing lost._

---

Hermes is a self-hosted workflow orchestration platform built for production environments where **no task can be lost**.

It is designed for engineering teams running large numbers of backend microservices who need full auditability — every task submitted, every retry attempted, every failure recorded, every worker's health tracked in real time.

When something fails, Hermes retries it. When retries are exhausted, it remembers. When a worker is broken, it stops trusting it — automatically.

---

## Core Capabilities

| Capability             | How                                                                 |
| ---------------------- | ------------------------------------------------------------------- |
| Durable task execution | Kafka + Zookeeper — tasks survive process restarts                  |
| Internal communication | gRPC — typed contract between coordinator and workers               |
| Automatic retry        | Exponential backoff up to `max_attempts`                            |
| Dead letter queue      | Exhausted tasks preserved, never silently dropped                   |
| Circuit breaker        | Per-worker CLOSED → OPEN → HALF_OPEN state machine                  |
| Distributed tracing    | OpenTelemetry — full request trace across all services in Jaeger    |
| Live metrics           | Prometheus + Grafana — task rates, durations, circuit breaker state |
| Web dashboard          | Next.js — live execution list, worker health, DLQ inspection        |
| Load tested            | 578 requests, 0% failure rate, 9+ RPS under 20 concurrent users     |
| CI/CD                  | GitHub Actions — import checks + Docker build on every push         |

---

## Stack

```
Coordinator     FastAPI + PostgreSQL + gRPC server
Workers         Python + Kafka consumer + gRPC client
Task Queue      Apache Kafka + Zookeeper
Tracing         OpenTelemetry → Jaeger
Metrics         Prometheus → Grafana
Dashboard       Next.js + shadcn/ui
Infrastructure  Docker Compose
CI              GitHub Actions
```

---

## Running Locally

**Prerequisites:** Docker Desktop, Docker Compose, Node.js (for dashboard)

```bash
git clone https://github.com/Nathan-sudo-pycharm/hermes.git
cd hermes
docker compose up
```

| Service            | URL                        |
| ------------------ | -------------------------- |
| REST API + Swagger | http://localhost:8080/docs |
| Dashboard          | http://localhost:3000      |
| Grafana            | http://localhost:3001      |
| Jaeger             | http://localhost:16686     |
| Prometheus         | http://localhost:9090      |

---

## Repository Structure

```
hermes/
├── coordinator/      # FastAPI + gRPC server — orchestration logic
├── worker/           # Kafka consumer + gRPC client — task execution
├── frontend/         # Next.js dashboard
├── proto/            # Protobuf contract (source of truth)
├── monitoring/       # Prometheus, Grafana, OTel Collector config
├── docs/             # Engineering notes, ADRs, architecture
└── locustfile.py     # Load test definition
```

---

## Documentation

| Document                                          | Description                                     |
| ------------------------------------------------- | ----------------------------------------------- |
| [Architecture](docs/ARCHITECTURE.md)              | System design, component breakdown, data flow   |
| [ADR-001](docs/adr-001-kafka-vs-redis-streams.md) | Kafka vs Redis Streams                          |
| [ADR-002](docs/adr-002-grpc-vs-rest-internal.md)  | gRPC vs REST for internal comms                 |
| [ADR-003](docs/adr-003-circuit-breaker-design.md) | Circuit breaker placement                       |
| [Day notes](docs/)                                | Session-by-session engineering logs (Days 3–14) |

---

## Built By

**Nathan Ivor Sequeira**  
BCA Graduate — St. Aloysius College (Autonomous), Mangaluru  
[GitHub](https://github.com/Nathan-sudo-pycharm) · [Portfolio](https://nathansequeirafinal.vercel.app)

---

_Named after the Greek messenger god. He delivered everything. He lost nothing._
