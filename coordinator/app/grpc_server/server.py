import sys
import os
import logging
import grpc
import grpc.aio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated'))
import hermes_pb2_grpc

from app.grpc_server.handlers import TaskServiceHandler

logger = logging.getLogger(__name__)


async def start_grpc_server():
    server = grpc.aio.server()
    hermes_pb2_grpc.add_TaskServiceServicer_to_server(TaskServiceHandler(), server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    logger.info("gRPC server listening on port 50051")
    return server