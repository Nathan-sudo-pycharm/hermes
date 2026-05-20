from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.kafka.consumer import start_consumer
    task = asyncio.create_task(start_consumer())
    logger.info("Kafka consumer started")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Kafka consumer stopped")


app = FastAPI(
    title="Hermes Worker",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    from app.core.config import settings
    return {
        "status": "ok",
        "worker_id": settings.WORKER_ID,
        "failure_rate": settings.WORKER_FAILURE_RATE,
        "task_duration": settings.WORKER_TASK_DURATION,
    }


@app.post("/debug/failure-rate")
async def set_failure_rate(body: dict):
    from app.core.config import settings
    if not settings.ENABLE_DEBUG_ENDPOINTS:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Debug endpoints disabled")
    rate = body.get("rate", 0.0)
    settings.WORKER_FAILURE_RATE = rate
    return {"worker_id": settings.WORKER_ID, "failure_rate": rate}