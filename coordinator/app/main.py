from confluent_kafka.admin import AdminClient

from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text, select
from app.database import engine, Base, AsyncSessionLocal
from app.routers import auth, workflows
from app.routers import dlq, workers
from app.grpc_server.server import start_grpc_server
from app.retry.scheduler import retry_scheduler
from app.models import Worker
from app.core.telemetry import setup_telemetry
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
import asyncio
import logging

logger = logging.getLogger(__name__)

setup_telemetry()


async def seed_workers():
    known_workers = [
        {"id": "worker-a", "grpc_address": "worker-a:50052"},
        {"id": "worker-b", "grpc_address": "worker-b:50052"},
        {"id": "worker-c", "grpc_address": "worker-c:50052"},
    ]
    async with AsyncSessionLocal() as session:
        for w in known_workers:
            existing = await session.execute(
                select(Worker).where(Worker.id == w["id"])
            )
            if not existing.scalar_one_or_none():
                session.add(Worker(id=w["id"], grpc_address=w["grpc_address"]))
                logger.info(f"Registered worker: {w['id']}")
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    await seed_workers()
    grpc_server    = await start_grpc_server()
    scheduler_task = asyncio.create_task(retry_scheduler())

    yield

    scheduler_task.cancel()
    await grpc_server.stop(grace=5)
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Hermes Coordinator",
    description="Distributed workflow orchestration platform",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app)

app.include_router(auth.router)
app.include_router(workflows.router)
app.include_router(dlq.router)
app.include_router(workers.router)

app.mount("/metrics", make_asgi_app())


def _kafka_check():
    """
    Synchronous Kafka connectivity check.
    Must be run in a thread executor — AdminClient is blocking.
    """
    admin = AdminClient({
        "bootstrap.servers": "kafka:29092",
        "socket.timeout.ms": 2000
    })
    admin.list_topics(timeout=2)


@app.get("/health")
async def health():
    """
    Liveness probe.
    Checks DB and Kafka connectivity.
    Kafka check runs in thread pool to avoid blocking the asyncio event loop.
    Returns degraded if either dependency is down.
    """
    db_status    = "ok"
    kafka_status = "ok"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _kafka_check)
    except Exception as e:
        kafka_status = f"error: {str(e)}"

    overall = "ok" if db_status == "ok" and kafka_status == "ok" else "degraded"

    return {
        "status":   overall,
        "database": db_status,
        "kafka":    kafka_status,
        "version":  "0.1.0"
    }


@app.get("/ready")
async def ready():
    """
    Readiness probe.
    Returns 200 only if ALL dependencies are healthy.
    Returns 503 if any dependency is down.
    Used by container orchestrators to route traffic only to healthy instances.
    """
    db_ok    = True
    kafka_ok = True

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _kafka_check)
    except Exception:
        kafka_ok = False

    if db_ok and kafka_ok:
        return {"ready": True}

    return Response(
        content='{"ready": false, "database": ' + str(db_ok).lower() +
                ', "kafka": ' + str(kafka_ok).lower() + '}',
        status_code=503,
        media_type="application/json"
    )