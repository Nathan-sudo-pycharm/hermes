# Apache Kafka — Learning Notes

> Reference: [Kafka in 10 Minutes](https://www.youtube.com/watch?v=QkdkLdMBuL0)

---

## The Problem Kafka Solves

Consider an online store. When a customer places an order, that single event triggers a chain reaction across multiple services:

- Database needs to be updated
- Sales dashboard needs to reflect the new order
- A notification needs to be sent to the customer

As order volume grows, this becomes a problem. If services are **tightly coupled** — meaning they talk directly to each other — one failure brings everything down. For example, if the payment service goes down, the entire order process freezes.

Kafka solves this by sitting **in between** services, decoupling them from each other.

---

## What is Kafka?

Apache Kafka is a **distributed event streaming platform**. Think of it like a post office — services drop off messages (events), and Kafka delivers them to whoever needs them, whenever they need them.

- Services don't talk directly to each other
- No tight coupling — one service going down does not freeze the others
- Highly scalable — built to handle massive volumes of events

---

## Core Concepts

### Event
When something happens in your system (e.g. an order is placed), Kafka captures it as an **event**.

An event contains:
- **Key** — identifies what the event is about (e.g. order ID)
- **Value** — the actual data (e.g. order details)
- **Metadata** — timestamp, topic, partition info, etc.

---

### Topics
Events are organised into **topics** — a topic groups the same type of events together.

- Example: all payment-related events go into a `payments` topic
- The engineer decides how to group events into topics
- Services **subscribe** to topics they care about — when a new event arrives in a topic, all subscribers are notified

> **Is Kafka a replacement for a database?**
> **No.** Kafka is not a database. It is a message streaming system. Use a database for persistent storage and querying — use Kafka for real-time event delivery between services.

---

### Partitions
Each topic is split into **partitions** for scalability.

- Think of it like a post office with multiple sections — more sections means more workers can process mail in parallel
- Partitions allow Kafka to handle large volumes of events efficiently
- Events within a partition are ordered; across partitions they are not

---

### Consumer Groups
When multiple instances of a microservice are running, they can all consume from Kafka partitions **in parallel** using a **consumer group**.

- Each instance in the group reads from a different partition
- Work is distributed automatically — no instance processes the same event twice
- Configured using the `group.id` attribute

---

### Kafka Brokers
A **broker** is a Kafka server — it is where the actual topic data is stored.

- Kafka runs as a cluster of brokers for fault tolerance
- Data is **replicated** across multiple brokers, so if one goes down, data is not lost
- Unlike traditional message queues (e.g. RabbitMQ) which delete a message once it is consumed, Kafka **retains messages on disk** for a configurable retention period — this allows replaying events and analysing historical patterns

---

### Streams API
Kafka includes a **Streams API** for processing a continuous flow of data in real time.

Use cases:
- Driver location updates in a ride-sharing app
- Live sales dashboard updates
- Real-time fraud detection

Streams allow you to process, transform, and react to events as they arrive — not in batches.

---

## Zookeeper vs KRaft

### Zookeeper (older)
Kafka traditionally relied on **Zookeeper** as a caretaker service — it monitored the brokers, managed leader election, and kept the cluster coordinated. Running Kafka meant running Zookeeper alongside it, adding operational overhead.

### KRaft (Kafka 3.0+)
Kafka 3.0 introduced **KRaft mode**, which removes the dependency on Zookeeper entirely. Kafka now handles its own coordination internally — simpler to run, fewer moving parts.

> In Hermes, we use Kafka with Zookeeper (the traditional setup) — documented as a known limitation. The production fix would be to migrate to KRaft mode.

---

## Kafka vs Traditional Message Queues

| | Kafka | RabbitMQ / Others |
|---|---|---|
| Message retention | Configurable (days, weeks) | Deleted after consumed |
| Scalability | Very high (partitions) | Moderate |
| Replay events | Yes | No |
| Real-time streaming | Yes (Streams API) | Limited |
| Use case | Event streaming, analytics | Task queues, simple messaging |

---

## Summary — Why Kafka in Hermes

Hermes uses Kafka as its task queue because:

- Messages survive worker crashes (durable, disk-backed)
- Consumer groups allow multiple workers to process tasks in parallel
- Partition-based model maps naturally to distributing work across workers
- Retention means failed tasks can be replayed or inspected in the dead letter queue

---

*Notes from Day 2 — Hermes build, May 2026.*