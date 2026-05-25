from prometheus_client import Counter, Histogram, Gauge

# Counts every completed task, labelled by worker and outcome
tasks_total = Counter(
    "hermes_tasks_total",
    "Total tasks completed",
    ["worker_id", "status"]   # status: success | failed | dead_lettered
)

# Tracks how long tasks take — useful for spotting slow workers
task_duration_seconds = Histogram(
    "hermes_task_duration_seconds",
    "Task execution duration in seconds",
    ["worker_id"],
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Counts every workflow execution submitted
workflow_executions_total = Counter(
    "hermes_workflow_executions_total",
    "Total workflow executions started"
)

# Live circuit breaker state per worker
# 0 = CLOSED (healthy), 1 = OPEN (tripped), 2 = HALF_OPEN (probing)
circuit_breaker_state = Gauge(
    "hermes_circuit_breaker_state",
    "Circuit breaker state per worker (0=CLOSED 1=OPEN 2=HALF_OPEN)",
    ["worker_id"]
)