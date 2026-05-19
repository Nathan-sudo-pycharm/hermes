from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models import User, WorkflowDefinition, WorkflowExecution
from app.schemas import (
    WorkflowDefinitionCreate,
    WorkflowDefinitionResponse,
    WorkflowExecuteRequest,
    WorkflowExecutionResponse
)
from app.auth import get_current_user
import uuid

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/definitions", response_model=WorkflowDefinitionResponse, status_code=201)
async def create_definition(
    body: WorkflowDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Register a new workflow definition.
    Requires JWT authentication.
    Steps are stored as JSONB in the database.
    """
    # Check if a definition with this name already exists
    result = await db.execute(
        select(WorkflowDefinition).where(WorkflowDefinition.name == body.name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow definition '{body.name}' already exists"
        )

    # Convert Pydantic step models to plain dicts for JSONB storage
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
    """
    List all registered workflow definitions.
    Requires JWT authentication.
    """
    result = await db.execute(select(WorkflowDefinition))
    definitions = result.scalars().all()
    return definitions


@router.post("/execute", response_model=WorkflowExecutionResponse, status_code=201)
async def execute_workflow(
    body: WorkflowExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a workflow for execution.
    Creates a workflow execution record in PENDING state.
    Kafka publishing will be added on Day 5.
    """
    # Verify the workflow definition exists
    result = await db.execute(
        select(WorkflowDefinition).where(WorkflowDefinition.id == body.definition_id)
    )
    definition = result.scalar_one_or_none()
    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow definition not found"
        )

    # Create execution record
    execution = WorkflowExecution(
        definition_id=body.definition_id,
        state="PENDING",
        input_payload=body.input_payload,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return execution


@router.get("/executions", response_model=List[WorkflowExecutionResponse])
async def list_executions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all workflow executions.
    Requires JWT authentication.
    """
    result = await db.execute(select(WorkflowExecution))
    executions = result.scalars().all()
    return executions


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific workflow execution.
    Requires JWT authentication.
    """
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    return execution