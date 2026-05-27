# ADR-002 — Internal Communication: gRPC vs REST

**Date:** 05-2026
**Status:** Accepted  
**Author:** Nathan Ivor Sequeira

---

## Context

After a worker executes a task, it must report the result back to the coordinator. The coordinator then updates the database and transitions the workflow state.

Two communication patterns were evaluated: gRPC and REST (HTTP/JSON).

---

## Options Considered

### Option A — gRPC

gRPC is a high-performance RPC framework that uses Protocol Buffers (protobuf) as its wire format. The interface is defined in a `.proto` file — a typed contract that both sides must conform to.

**Strengths:**

- Typed contract enforced at code generation time — client and server cannot drift out of sync
- Binary serialisation — smaller payload, faster than JSON
- `grpc.aio` integrates cleanly with Python asyncio
- The `.proto` file serves as living documentation of the interface
- Bidirectional streaming available for future use (e.g. live task progress)

**Weaknesses:**

- Requires code generation step (`protoc`) — adds build complexity
- Harder to debug than REST — binary format not human-readable
- Not directly testable via browser or Swagger

### Option B — REST (HTTP/JSON)

Workers call back to a coordinator REST endpoint with a JSON payload.

**Strengths:**

- No code generation — just define an endpoint and call it
- Human-readable — easy to test with curl or Postman
- Already used for the public API

**Weaknesses:**

- No enforced contract — client and server can diverge silently
- JSON serialisation overhead on the hot path (every task result)
- No built-in streaming support

---

## Decision

**gRPC was chosen.**

The enforced contract is the decisive factor. In a distributed system with multiple workers calling back to a single coordinator, silent contract drift is a real operational risk. A change to the result payload that isn't reflected on both sides would cause silent data corruption — tasks marked incorrectly, workflow states never updated. The `.proto` file makes this impossible: any mismatch causes a build-time failure, not a runtime mystery.

The binary performance benefit is secondary but real — on the result reporting hot path, every task calls `ReportResult`. At scale, the cumulative difference between JSON and protobuf serialisation is meaningful.

---

## Consequences

- `proto/hermes.proto` is the single source of truth for the internal API contract
- Proto files are copied to each service directory for independent Docker builds
- Generated stubs are committed to the repository and verified in CI
- The coordinator runs two servers simultaneously: FastAPI (port 8000) and gRPC (port 50051)
- gRPC calls are not exposed externally — only accessible within the Docker network
