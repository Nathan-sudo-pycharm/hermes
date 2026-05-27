# ADR-001 — Task Queue: Kafka vs Redis Streams

**Date:** 05-2026
**Status:** Accepted  
**Author:** Nathan Ivor Sequeira

---

## Context

Hermes needs a durable task queue that:

- Decouples the coordinator from workers
- Survives process restarts without losing tasks
- Allows multiple workers to consume tasks concurrently
- Supports replaying messages if a worker crashes mid-processing

Two candidates were evaluated: Apache Kafka and Redis Streams.

---

## Options Considered

### Option A — Apache Kafka

Kafka is a distributed event streaming platform. It stores messages durably on disk in an append-only log. Consumers track their own offset — meaning they can replay from any point in the log. Multiple consumer groups can read the same topic independently.

**Strengths:**

- Messages persisted to disk — survive broker restarts
- Consumer offset tracking — worker can resume exactly where it left off after a crash
- Consumer groups — Kafka distributes partitions across workers automatically
- Topic partitioning — ordering guaranteed within a partition
- The `traceparent` field in messages enables distributed tracing across the Kafka boundary

**Weaknesses:**

- Requires Zookeeper (or KRaft in newer versions) — adds operational complexity
- Heavier resource footprint than Redis
- No native delayed delivery — retry backoff requires a scheduler

### Option B — Redis Streams

Redis Streams is a log data structure built into Redis. Similar consumer group model to Kafka. Redis is already a common dependency in many stacks.

**Strengths:**

- Simpler operational setup — single Redis process
- Lower resource footprint
- Built-in support for pending entry lists (unacknowledged messages)

**Weaknesses:**

- Data stored in memory by default — messages lost on Redis restart unless persistence is explicitly configured (AOF/RDB)
- Less battle-tested for high-throughput distributed systems
- Smaller ecosystem of tooling and observability integrations

---

## Decision

**Kafka was chosen.**

The primary reason is durability. Hermes is designed around the principle that nothing should be lost — this is stated explicitly in the project tagline. A task queue that can lose messages on restart is incompatible with that design goal.

The secondary reason is ecosystem maturity. Kafka has first-class support in OpenTelemetry (via `traceparent` propagation), Prometheus (via JMX exporter), and Grafana. Redis Streams would require more custom integration work for the same observability coverage.

The operational overhead of Zookeeper is accepted as a tradeoff — for a self-hosted deployment, this is manageable.

---

## Consequences

- Zookeeper runs as a required sidecar container alongside Kafka
- The retry scheduler must manage backoff delay externally (Kafka has no native delayed delivery)
- Message replay is available via `auto.offset.reset: earliest` for debugging
- Kafka becomes a hard dependency — if Kafka is down, no tasks can be submitted
