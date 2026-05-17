from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.database import engine, Base
from app.core.config import settings
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

@app.get("/health")
async def health():
    # Check database connectivity
    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "kafka": "not checked at startup",
        "version": "0.1.0"
    }