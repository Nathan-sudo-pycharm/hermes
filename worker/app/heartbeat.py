import asyncio
import logging
from app.grpc_client.client import send_heartbeat

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30


async def heartbeat_loop():
    logger.info("Heartbeat loop started")
    while True:
        await send_heartbeat(state="idle", active_tasks=0)
        await asyncio.sleep(HEARTBEAT_INTERVAL)