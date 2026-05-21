import sys
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated'))
import hermes_pb2
import hermes_pb2_grpc

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import TaskExecution, WorkflowExecution

logger = logging.getLogger(__name__)


def compute_backoff(attempt_number: int) -> int:
    """
    Exponential backoff: 2^attempt seconds, capped at 30s.
    attempt 1 → 2s, attempt 2 → 4s, attempt 3 → 8s, max 30s.
    """
    return int(min(2 ** attempt_number, 30))


class TaskServiceHandler(hermes_pb2_grpc.TaskServiceServicer):

    async def ReportResult(self, request, context):
        task_id   = request.task_execution_id
        worker_id = request.worker_id
        success   = request.success

        logger.info(f"ReportResult: task={task_id} worker={worker_id} success={success}")

        async with AsyncSessionLocal() as session:

            # --- 1. Fetch the task row ---
            result = await session.execute(
                select(TaskExecution).where(TaskExecution.id == uuid.UUID(task_id))
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task {task_id} not found in DB")
                return hermes_pb2.WorkerAck(received=False)

            now = datetime.now(timezone.utc)

            # --- 2. Update current task row ---
            task.worker_id    = worker_id
            task.duration_ms  = request.duration_ms
            task.completed_at = now

            if success:
                task.state = "SUCCESS"

            else:
                task.state     = "FAILED"
                task.error_msg = request.error_msg

                if task.attempt_number < task.max_attempts:
                    # --- 3a. Retries remaining — schedule next attempt ---
                    delay        = compute_backoff(task.attempt_number)
                    next_attempt = task.attempt_number + 1

                    retry_task = TaskExecution(
                        id               = uuid.uuid4(),
                        execution_id     = task.execution_id,
                        step_name        = task.step_name,
                        step_index       = task.step_index,
                        state            = "RETRYING",
                        idempotency_key  = f"{task.execution_id}:{task.step_index}:{next_attempt}",
                        attempt_number   = next_attempt,
                        max_attempts     = task.max_attempts,
                        next_retry_at    = now + timedelta(seconds=delay),
                        queued_at        = now,
                    )
                    session.add(retry_task)
                    logger.info(
                        f"Task {task_id} FAILED — retry {next_attempt}/{task.max_attempts} "
                        f"scheduled in {delay}s"
                    )

                else:
                    # --- 3b. All attempts exhausted — Dead Letter Queue ---
                    task.state = "DEAD_LETTERED"
                    logger.warning(
                        f"Task {task_id} DEAD_LETTERED after {task.attempt_number} attempts"
                    )

                    from app.kafka.producer import publish_task
                    await publish_task(
                        {
                            "task_execution_id": str(task.id),
                            "execution_id":      str(task.execution_id),
                            "step_name":         task.step_name,
                            "step_index":        task.step_index,
                            "attempt_number":    task.attempt_number,
                            "error_msg":         request.error_msg,
                            "dead_lettered_at":  now.isoformat(),
                        },
                        topic="hermes.tasks.dlq"
                    )

            # --- 4. Re-evaluate workflow state ---
            all_tasks_result = await session.execute(
                select(TaskExecution).where(
                    TaskExecution.execution_id == task.execution_id
                )
            )
            all_tasks = all_tasks_result.scalars().all()
            states = [t.state for t in all_tasks]

            wf_result = await session.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == task.execution_id)
            )
            workflow = wf_result.scalar_one_or_none()

            if workflow:
                if all(s == "SUCCESS" for s in states):
                    workflow.state        = "COMPLETED"
                    workflow.completed_at = now
                    logger.info(f"Workflow {task.execution_id} COMPLETED")

                elif any(s == "DEAD_LETTERED" for s in states):
                    workflow.state        = "FAILED"
                    workflow.completed_at = now
                    workflow.error_msg    = f"Task exhausted retries: {request.error_msg}"
                    logger.warning(f"Workflow {task.execution_id} FAILED — task dead-lettered")

                else:
                    # RETRYING tasks are still in-flight — workflow stays RUNNING
                    workflow.state = "RUNNING"

            await session.commit()

        return hermes_pb2.WorkerAck(received=True)


    async def Heartbeat(self, request, context):
        logger.info(f"Heartbeat: worker={request.worker_id} state={request.state}")
        return hermes_pb2.HeartbeatAck(accepted=True)