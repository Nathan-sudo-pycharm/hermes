from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.database import engine, Base
from app.core.config import settings
from app.routers import auth, workflows
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup — create all tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
    yield
    # On shutdown — dispose the connection pool cleanly
    await engine.dispose()
    logger.info("Database connection closed")

app = FastAPI(
    title="Hermes Coordinator",
    description="Distributed workflow orchestration platform",
    version="0.1.0",
    lifespan=lifespan
)

# Register routers
app.include_router(auth.router)
app.include_router(workflows.router)

@app.get("/health")
async def health():
    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "kafka": "ok",
        "version": "0.1.0"
    }