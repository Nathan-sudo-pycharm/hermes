import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import TaskExecution

logger = logging.getLogger(__name__)


async def retry_scheduler():
    logger.info("Retry scheduler started")
    while True:
        try:
            await asyncio.sleep(2)
            now = datetime.now(timezone.utc)

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(TaskExecution).where(
                        TaskExecution.state == "RETRYING",
                        TaskExecution.next_retry_at <= now,
                    )
                )
                due_tasks = result.scalars().all()

                for task in due_tasks:
                    from app.kafka.producer import publish_task
                    await publish_task({
                        "task_execution_id": str(task.id),
                        "execution_id":      str(task.execution_id),
                        "step_name":         task.step_name,
                        "step_index":        task.step_index,
                        "idempotency_key":   task.idempotency_key,
                        "attempt_number":    task.attempt_number,
                        "max_retries":       task.max_attempts,
                        "timeout_seconds":   10,
                        "input_payload":     {},
                        "traceparent":       None,
                    })
                    task.state = "QUEUED"
                    logger.info(f"Re-queued task {task.id} attempt {task.attempt_number}")

                if due_tasks:
                    await session.commit()

        except Exception as e:
            logger.error(f"Scheduler error: {e}")