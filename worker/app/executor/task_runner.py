import asyncio
import random
import logging
from app.core.config import settings
logger = logging.getLogger(__name__)


async def run_task(task: dict) -> None:
    """
    Simulates task execution.
    - Sleeps for WORKER_TASK_DURATION seconds to simulate work
    - Randomly fails based on WORKER_FAILURE_RATE
    - Logs the result

    In a real system this would be replaced with actual business logic.
    """
    task_id = task["task_execution_id"]
    step_name = task["step_name"]

    logger.info(f"[{settings.WORKER_ID}] Starting task {task_id} step={step_name}")

    # Simulate work duration
    await asyncio.sleep(settings.WORKER_TASK_DURATION)

    # Simulate failure based on failure rate
    if random.random() < settings.WORKER_FAILURE_RATE:
        logger.error(f"[{settings.WORKER_ID}] Task {task_id} FAILED (simulated failure)")
        # gRPC result reporting will be added on Day 6
        return

    logger.info(f"[{settings.WORKER_ID}] Task {task_id} SUCCESS")
    # gRPC result reporting will be added on Day 6