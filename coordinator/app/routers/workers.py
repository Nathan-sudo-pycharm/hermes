from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Worker, CircuitBreakerState

router = APIRouter(prefix="/workers", tags=["workers"])


@router.get("/")
async def list_workers(db: AsyncSession = Depends(get_db)):
    workers_result = await db.execute(select(Worker))
    workers = workers_result.scalars().all()

    cb_result = await db.execute(select(CircuitBreakerState))
    cb_states = {cb.worker_id: cb for cb in cb_result.scalars().all()}

    return [
        {
            "id":                w.id,
            "grpc_address":      w.grpc_address,
            "last_heartbeat_at": w.last_heartbeat_at,
            "circuit_breaker": {
                "state":           cb_states[w.id].state if w.id in cb_states else "CLOSED",
                "failure_count":   cb_states[w.id].failure_count if w.id in cb_states else 0,
                "opened_at":       cb_states[w.id].opened_at if w.id in cb_states else None,
                "next_retry_at":   cb_states[w.id].next_retry_at if w.id in cb_states else None,
            }
        }
        for w in workers
    ]