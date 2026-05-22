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
from app.models import TaskExecution, WorkflowExecution, Worker
from app.circuit_breaker.engine import record_failure, record_success, check_transition

logger = logging.getLogger(__name__)


def compute_backoff(attempt_number: int) -> int:
    return int(min(2 ** attempt_number, 30))


class TaskServiceHandler(hermes_pb2_grpc.TaskServiceServicer):

    async def ReportResult(self, request, context):
        task_id   = request.task_execution_id
        worker_id = request.worker_id
        success   = request.success

        logger.info(f"ReportResult: task={task_id} worker={worker_id} success={success}")

        async with AsyncSessionLocal() as session:

            result = await session.execute(
                select(TaskExecution).where(TaskExecution.id == uuid.UUID(task_id))
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task {task_id} not found in DB")
                return hermes_pb2.WorkerAck(received=False)

            now = datetime.now(timezone.utc)
            task.worker_id    = worker_id
            task.duration_ms  = request.duration_ms
            task.completed_at = now

            if success:
                task.state = "SUCCESS"
                await record_success(session, worker_id)

            else:
                task.state     = "FAILED"
                task.error_msg = request.error_msg
                await record_failure(session, worker_id)

                if task.attempt_number < task.max_attempts:
                    delay        = compute_backoff(task.attempt_number)
                    next_attempt = task.attempt_number + 1

                    retry_task = TaskExecution(
                        id              = uuid.uuid4(),
                        execution_id    = task.execution_id,
                        step_name       = task.step_name,
                        step_index      = task.step_index,
                        state           = "RETRYING",
                        idempotency_key = f"{task.execution_id}:{task.step_index}:{next_attempt}",
                        attempt_number  = next_attempt,
                        max_attempts    = task.max_attempts,
                        next_retry_at   = now + timedelta(seconds=delay),
                        queued_at       = now,
                    )
                    session.add(retry_task)
                    logger.info(f"Retry {next_attempt}/{task.max_attempts} in {delay}s")

                else:
                    task.state = "DEAD_LETTERED"
                    logger.warning(f"Task {task_id} DEAD_LETTERED")

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

            # Workflow state
            all_tasks_result = await session.execute(
                select(TaskExecution).where(
                    TaskExecution.execution_id == task.execution_id
                )
            )
            all_tasks = all_tasks_result.scalars().all()
            states    = [t.state for t in all_tasks]

            wf_result = await session.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == task.execution_id)
            )
            workflow = wf_result.scalar_one_or_none()

            if workflow:
                if all(s == "SUCCESS" for s in states):
                    workflow.state        = "COMPLETED"
                    workflow.completed_at = now
                elif any(s == "DEAD_LETTERED" for s in states):
                    workflow.state        = "FAILED"
                    workflow.completed_at = now
                    workflow.error_msg    = f"Task exhausted retries: {request.error_msg}"
                else:
                    workflow.state = "RUNNING"

            await session.commit()

        return hermes_pb2.WorkerAck(received=True)


    async def Heartbeat(self, request, context):
        worker_id = request.worker_id
        logger.info(f"Heartbeat: worker={worker_id} state={request.state}")

        async with AsyncSessionLocal() as session:
            # Upsert worker record
            result = await session.execute(
                select(Worker).where(Worker.id == worker_id)
            )
            worker = result.scalar_one_or_none()

            now = datetime.now(timezone.utc)
            if worker:
                worker.last_heartbeat_at = now
            else:
                session.add(Worker(
                    id               = worker_id,
                    grpc_address     = f"{worker_id}:50052",
                    last_heartbeat_at = now,
                ))

            # Check if OPEN circuit should transition to HALF_OPEN
            await check_transition(session, worker_id)
            await session.commit()

        return hermes_pb2.HeartbeatAck(accepted=True)