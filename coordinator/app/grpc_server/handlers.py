import sys
import os
import uuid
import logging
from datetime import datetime, timezone

# Tell Python where the generated gRPC files live
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated'))
import hermes_pb2
import hermes_pb2_grpc

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import TaskExecution, WorkflowExecution

logger = logging.getLogger(__name__)


class TaskServiceHandler(hermes_pb2_grpc.TaskServiceServicer):

    async def ReportResult(self, request, context):
        task_id  = request.task_execution_id
        worker_id = request.worker_id
        success  = request.success

        logger.info(f"ReportResult: task={task_id} worker={worker_id} success={success}")

        async with AsyncSessionLocal() as session:
            # 1. Find the task row
            result = await session.execute(
                select(TaskExecution).where(TaskExecution.id == uuid.UUID(task_id))
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task {task_id} not found in DB")
                return hermes_pb2.WorkerAck(received=False)

            # 2. Update task fields
            now = datetime.now(timezone.utc)
            task.state       = "SUCCESS" if success else "FAILED"
            task.worker_id   = worker_id
            task.duration_ms = request.duration_ms
            task.completed_at = now
            if not success:
                task.error_msg = request.error_msg

            # 3. Check if the whole workflow is done
            all_tasks_result = await session.execute(
                select(TaskExecution).where(
                    TaskExecution.execution_id == task.execution_id
                )
            )
            all_tasks = all_tasks_result.scalars().all()
            states = [t.state for t in all_tasks]

            # 4. Update workflow state
            wf_result = await session.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.id == task.execution_id
                )
            )
            workflow = wf_result.scalar_one_or_none()

            if workflow:
                if all(s == "SUCCESS" for s in states):
                    workflow.state = "COMPLETED"
                    workflow.completed_at = now
                    logger.info(f"Workflow {task.execution_id} COMPLETED")
                elif any(s == "FAILED" for s in states):
                    workflow.state = "FAILED"
                    workflow.completed_at = now
                    workflow.error_msg = f"Step failed: {request.error_msg}"
                    logger.info(f"Workflow {task.execution_id} FAILED")
                else:
                    workflow.state = "RUNNING"

            await session.commit()

        return hermes_pb2.WorkerAck(received=True)

    async def Heartbeat(self, request, context):
        logger.info(f"Heartbeat: worker={request.worker_id} state={request.state}")
        return hermes_pb2.HeartbeatAck(accepted=True)