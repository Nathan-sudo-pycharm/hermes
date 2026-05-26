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
import asyncio
import logging

logger = logging.getLogger(__name__)

# Initialise OpenTelemetry tracing before the app is created.
# Must be called at module level so all routes are instrumented.
setup_telemetry()


async def seed_workers():
    """
    Inserts the three known workers into the DB on startup.
    Checks before inserting to avoid duplicate key errors on restart.
    Workers are statically known from docker-compose.
    On Day 8+, heartbeats keep these records updated dynamically.
    """
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
    """
    Runs on startup and shutdown.
    Order matters:
      1. Create DB tables (idempotent — safe to run on every restart)
      2. Seed known workers into the workers table
      3. Start the gRPC server on port 50051
      4. Start the retry scheduler as a background asyncio task
    On shutdown: cancel scheduler, stop gRPC server, close DB connections.
    """
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

# Allow the Next.js dashboard running on localhost:3000 to call the API.
# Without this, browsers block cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-instrument FastAPI — creates an OTel span for every HTTP request.
FastAPIInstrumentor.instrument_app(app)

# Register all routers
app.include_router(auth.router)
app.include_router(workflows.router)
app.include_router(dlq.router)
app.include_router(workers.router)

# Expose Prometheus metrics at /metrics.
# Prometheus scrapes this endpoint every 15 seconds.
app.mount("/metrics", make_asgi_app())


@app.get("/health")
async def health():
    """
    Health check endpoint.
    Verifies DB connectivity and returns coordinator version.
    """
    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    return {
        "status":   "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "version":  "0.1.0"
    }