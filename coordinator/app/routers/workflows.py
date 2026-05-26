from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models import User, WorkflowDefinition, WorkflowExecution, TaskExecution
from app.schemas import (
    WorkflowDefinitionCreate,
    WorkflowDefinitionResponse,
    WorkflowExecuteRequest,
    WorkflowExecutionResponse
)
from app.auth import get_current_user
from app.kafka.producer import publish_task
from app.core.telemetry import get_tracer
from opentelemetry.propagate import inject
from opentelemetry import trace as otel_trace
from app.core.metrics import workflow_executions_total
from sqlalchemy.orm import selectinload
import uuid

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/definitions", response_model=WorkflowDefinitionResponse, status_code=201)
async def create_definition(
    body: WorkflowDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(WorkflowDefinition).where(WorkflowDefinition.name == body.name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow definition '{body.name}' already exists"
        )
    definition = WorkflowDefinition(
        name=body.name,
        steps=[step.model_dump() for step in body.steps]
    )
    db.add(definition)
    await db.commit()
    await db.refresh(definition)
    return definition


@router.get("/definitions", response_model=List[WorkflowDefinitionResponse])
async def list_definitions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(WorkflowDefinition))
    definitions = result.scalars().all()
    return definitions


@router.post("/execute", response_model=WorkflowExecutionResponse, status_code=201)
async def execute_workflow(
    body: WorkflowExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(WorkflowDefinition).where(WorkflowDefinition.id == body.definition_id)
    )
    definition = result.scalar_one_or_none()
    if not definition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow definition not found")

    execution = WorkflowExecution(
        definition_id=body.definition_id,
        state="RUNNING",
        input_payload=body.input_payload,
    )
    db.add(execution)
    await db.flush()

    first_step      = definition.steps[0]
    step_index      = 0
    attempt_number  = 1
    idempotency_key = f"{execution.id}:{step_index}:{attempt_number}"

    task = TaskExecution(
        execution_id    = execution.id,
        step_name       = first_step["name"],
        step_index      = step_index,
        state           = "QUEUED",
        idempotency_key = idempotency_key,
        attempt_number  = attempt_number,
        max_attempts    = first_step.get("max_retries", 3),
    )
    db.add(task)
    await db.commit()
    await db.refresh(execution)
    await db.refresh(task)

    tracer  = get_tracer()
    carrier = {}

    with tracer.start_as_current_span("execute_workflow") as span:
        span.set_attribute("workflow.execution_id", str(execution.id))
        span.set_attribute("workflow.definition",   definition.name)
        span.set_attribute("task.step_name",        first_step["name"])

        inject(carrier)

        ctx = span.get_span_context()
        execution.trace_id = format(ctx.trace_id, '032x')
        await db.commit()

        await publish_task({
            "task_execution_id": str(task.id),
            "execution_id":      str(execution.id),
            "step_name":         first_step["name"],
            "step_index":        step_index,
            "idempotency_key":   idempotency_key,
            "timeout_seconds":   first_step.get("timeout_seconds", 10),
            "max_retries":       first_step.get("max_retries", 3),
            "attempt_number":    attempt_number,
            "input_payload":     body.input_payload or {},
            "traceparent":       carrier.get("traceparent"),
        })

    workflow_executions_total.inc()

    # Reload with tasks eagerly loaded — prevents MissingGreenlet error
    # during Pydantic serialisation of the tasks relationship
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution.id)
        .options(selectinload(WorkflowExecution.tasks))
    )
    return result.scalar_one()


@router.get("/executions", response_model=List[WorkflowExecutionResponse])
async def list_executions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # selectinload required — tasks is a relationship field in the response schema.
    # Without it, Pydantic serialisation triggers lazy loading which fails
    # in async context (MissingGreenlet error).
    result = await db.execute(
        select(WorkflowExecution).options(selectinload(WorkflowExecution.tasks))
    )
    executions = result.scalars().all()
    return executions


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id)
        .options(selectinload(WorkflowExecution.tasks))
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return execution