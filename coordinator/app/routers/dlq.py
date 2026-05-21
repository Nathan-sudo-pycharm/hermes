from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import TaskExecution

router = APIRouter(prefix="/dlq", tags=["dlq"])


@router.get("/tasks")
async def list_dead_lettered(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TaskExecution).where(TaskExecution.state == "DEAD_LETTERED")
    )
    tasks = result.scalars().all()
    return [
        {
            "id":             str(t.id),
            "execution_id":   str(t.execution_id),
            "step_name":      t.step_name,
            "attempt_number": t.attempt_number,
            "error_msg":      t.error_msg,
            "completed_at":   t.completed_at,
        }
        for t in tasks
    ]