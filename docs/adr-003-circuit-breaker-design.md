# ADR-003 — Circuit Breaker: Coordinator vs Workers

**Date:** 2026-05  
**Status:** Accepted  
**Author:** Nathan Ivor Sequeira

---

## Context

Hermes needs a circuit breaker to detect failing workers and stop routing tasks to them temporarily. Two placement options were considered: implementing the circuit breaker in each worker (distributed), or centralising it in the coordinator.

---

## Options Considered

### Option A — Circuit breaker in each Worker

Each worker tracks its own failure rate and self-reports its health. The coordinator queries workers before dispatching tasks.

**Strengths:**

- Each worker has direct visibility into its own failures
- No single point of failure for circuit breaker state

**Weaknesses:**

- Requires workers to expose a health/state endpoint
- Coordinator must query every worker before each dispatch decision — adds latency
- State is distributed — difficult to get a consistent view across all workers
- If a worker crashes, its circuit breaker state is lost

### Option B — Circuit breaker in the Coordinator (chosen)

The coordinator maintains circuit breaker state for each worker in the PostgreSQL database. State is updated on every `ReportResult` gRPC call.

**Strengths:**

- Single source of truth — one DB table, one place to query
- State survives worker restarts — persisted in PostgreSQL
- The coordinator already receives every task result via gRPC — no additional calls needed to observe worker health
- State visible via REST API (`GET /workers/`) and Grafana dashboard

**Weaknesses:**

- Coordinator is a single point of failure for circuit breaker decisions
- With Kafka-based dispatch, the coordinator cannot prevent tasks from reaching an OPEN worker — enforcement is observational, not preventive, in this architecture

---

## Decision

**Coordinator-side circuit breaker was chosen.**

The coordinator already has complete visibility into worker outcomes — every task result flows through `ReportResult`. Placing the circuit breaker here requires no additional communication and keeps the state in a single durable location.

The limitation — that Kafka-based dispatch cannot be blocked by circuit breaker state — is acknowledged. In a future version, per-worker Kafka topics would allow the coordinator to stop publishing to a specific worker's topic when its circuit is OPEN. This is noted as a known limitation, not a design flaw.

---

## Consequences

- `circuit_breaker_state` table in PostgreSQL tracks state per worker
- State machine: CLOSED → OPEN (3 failures) → HALF_OPEN (30s timeout) → CLOSED (probe success)
- Circuit breaker state updated on every `ReportResult` call — zero additional overhead
- OPEN → HALF_OPEN transition triggered by worker Heartbeat — only considers recovery when the worker is provably alive
- Circuit breaker state exposed in Grafana as a gauge metric (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
