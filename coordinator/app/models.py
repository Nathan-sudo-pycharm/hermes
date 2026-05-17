import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# Stores registered users — used for JWT authentication
class User(Base):
    __tablename__ = "users"

    # UUID primary key — more secure than auto-increment integers
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # We never store plain text passwords — only the bcrypt hash
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


# Stores registered workers (worker-a, worker-b, worker-c)
class Worker(Base):
    __tablename__ = "workers"

    # Text primary key — we use human-readable IDs like "worker-a"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    # gRPC address the coordinator uses to reach this worker
    grpc_address: Mapped[str] = mapped_column(String, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    # Updated every time the worker sends a heartbeat
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # One worker has one circuit breaker state
    circuit_breaker: Mapped["CircuitBreakerState"] = relationship(back_populates="worker")


# Tracks the circuit breaker state per worker
# States: CLOSED (healthy), OPEN (rejecting tasks), HALF_OPEN (testing recovery)
class CircuitBreakerState(Base):
    __tablename__ = "circuit_breaker_state"

    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.id"), primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="CLOSED")
    # How many consecutive failures have occurred
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_failure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    # When the circuit was opened
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    # When the coordinator should attempt a probe task (HALF_OPEN transition)
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    worker: Mapped["Worker"] = relationship(back_populates="circuit_breaker")


# Workflow definitions are templates — they define the steps a workflow runs
class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Steps stored as JSON — list of dicts with name, timeout_seconds, max_retries
    # Example: [{"name": "validate", "timeout_seconds": 10, "max_retries": 3}]
    steps: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # One definition can have many execution instances
    executions: Mapped[list["WorkflowExecution"]] = relationship(back_populates="definition")


# A workflow execution is one run of a workflow definition
class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_definitions.id"))
    # PENDING, RUNNING, COMPLETED, FAILED, PARTIALLY_FAILED
    state: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    # The input data passed when submitting the workflow
    input_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    # OpenTelemetry trace ID — used to link to Jaeger trace
    trace_id: Mapped[str] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    error_msg: Mapped[str] = mapped_column(Text, nullable=True)

    definition: Mapped["WorkflowDefinition"] = relationship(back_populates="executions")
    # One execution has many task executions (one per step)
    tasks: Mapped[list["TaskExecution"]] = relationship(back_populates="execution")


# A task execution is one step within a workflow execution
class TaskExecution(Base):
    __tablename__ = "task_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"))
    step_name: Mapped[str] = mapped_column(String, nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # Which worker picked up this task
    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.id"), nullable=True)
    # QUEUED, ASSIGNED, RUNNING, SUCCESS, FAILED, RETRYING, DEAD_LETTERED
    state: Mapped[str] = mapped_column(String, nullable=False, default="QUEUED")
    # Unique key per attempt — prevents double execution if task is reassigned
    # Format: "{execution_id}:{step_index}:{attempt_number}"
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    # How long the task took in milliseconds
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    error_msg: Mapped[str] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    # When to retry if this task failed — calculated using exponential backoff
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    execution: Mapped["WorkflowExecution"] = relationship(back_populates="tasks")