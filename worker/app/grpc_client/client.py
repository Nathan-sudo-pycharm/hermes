import sys
import os
import logging
import grpc
import grpc.aio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated'))
import hermes_pb2
import hermes_pb2_grpc

from app.core.config import settings

logger = logging.getLogger(__name__)


async def report_result(
    task_execution_id: str,
    worker_id: str,
    success: bool,
    error_msg: str = "",
    duration_ms: int = 0
) -> bool:
    try:
        async with grpc.aio.insecure_channel(settings.COORDINATOR_GRPC_ADDRESS) as channel:
            stub = hermes_pb2_grpc.TaskServiceStub(channel)
            response = await stub.ReportResult(
                hermes_pb2.TaskResult(
                    task_execution_id=task_execution_id,
                    worker_id=worker_id,
                    success=success,
                    error_msg=error_msg,
                    duration_ms=duration_ms,
                )
            )
            logger.info(f"ReportResult ack: received={response.received}")
            return response.received
    except Exception as e:
        logger.error(f"gRPC ReportResult failed: {e}")
        return False


async def send_heartbeat(state: str = "idle", active_tasks: int = 0) -> bool:
    try:
        async with grpc.aio.insecure_channel(settings.COORDINATOR_GRPC_ADDRESS) as channel:
            stub = hermes_pb2_grpc.TaskServiceStub(channel)
            response = await stub.Heartbeat(
                hermes_pb2.HeartbeatRequest(
                    worker_id=settings.WORKER_ID,
                    state=state,
                    active_tasks=active_tasks,
                )
            )
            return response.accepted
    except Exception as e:
        logger.error(f"gRPC Heartbeat failed: {e}")
        return False