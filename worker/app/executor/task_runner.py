import asyncio
import random
import logging
import time

from app.core.config import settings
from app.grpc_client.client import report_result

logger = logging.getLogger(__name__)


async def run_task(task: dict) -> None:
    task_id   = task["task_execution_id"]
    step_name = task["step_name"]

    logger.info(f"[{settings.WORKER_ID}] Starting task {task_id} step={step_name}")

    # Record start time so we can calculate duration
    start_time = time.time()

    # Simulate work
    await asyncio.sleep(settings.WORKER_TASK_DURATION)

    duration_ms = int((time.time() - start_time) * 1000)
    failed = random.random() < settings.WORKER_FAILURE_RATE

    if failed:
        logger.error(f"[{settings.WORKER_ID}] Task {task_id} FAILED (simulated)")
        await report_result(
            task_execution_id=task_id,
            worker_id=settings.WORKER_ID,
            success=False,
            error_msg="Simulated task failure",
            duration_ms=duration_ms,
        )
    else:
        logger.info(f"[{settings.WORKER_ID}] Task {task_id} SUCCESS")
        await report_result(
            task_execution_id=task_id,
            worker_id=settings.WORKER_ID,
            success=True,
            duration_ms=duration_ms,
        )