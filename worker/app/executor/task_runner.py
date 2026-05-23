import asyncio
import random
import logging
import time

from opentelemetry.propagate import extract
from app.core.telemetry import get_tracer
from app.core.config import settings
from app.grpc_client.client import report_result

logger = logging.getLogger(__name__)


async def run_task(task: dict) -> None:
    task_id    = task["task_execution_id"]
    step_name  = task["step_name"]
    traceparent = task.get("traceparent")

    # Extract trace context from Kafka message
    # This links the worker span to the coordinator's trace
    carrier = {"traceparent": traceparent} if traceparent else {}
    ctx     = extract(carrier)

    tracer = get_tracer()
    with tracer.start_as_current_span("run_task", context=ctx) as span:
        span.set_attribute("task.execution_id", task_id)
        span.set_attribute("task.step_name",    step_name)
        span.set_attribute("worker.id",         settings.WORKER_ID)

        logger.info(f"[{settings.WORKER_ID}] Starting task {task_id} step={step_name}")

        start_time = time.time()
        await asyncio.sleep(settings.WORKER_TASK_DURATION)
        duration_ms = int((time.time() - start_time) * 1000)

        failed = random.random() < settings.WORKER_FAILURE_RATE

        if failed:
            span.set_attribute("task.success", False)
            logger.error(f"[{settings.WORKER_ID}] Task {task_id} FAILED (simulated)")
            await report_result(
                task_execution_id=task_id,
                worker_id=settings.WORKER_ID,
                success=False,
                error_msg="Simulated task failure",
                duration_ms=duration_ms,
            )
        else:
            span.set_attribute("task.success", True)
            logger.info(f"[{settings.WORKER_ID}] Task {task_id} SUCCESS")
            await report_result(
                task_execution_id=task_id,
                worker_id=settings.WORKER_ID,
                success=True,
                duration_ms=duration_ms,
            )