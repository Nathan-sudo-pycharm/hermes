from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# --- Auth schemas ---

class UserRegister(BaseModel):
    """Request body for POST /auth/register"""
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """Request body for POST /auth/login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response body for successful login"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user info returned after registration"""
    id: UUID
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Workflow schemas ---

class WorkflowStep(BaseModel):
    """One step inside a workflow definition"""
    name: str
    timeout_seconds: int = 10
    max_retries: int = 3


class WorkflowDefinitionCreate(BaseModel):
    """Request body for POST /workflows/definitions"""
    name: str
    steps: List[WorkflowStep]


class WorkflowDefinitionResponse(BaseModel):
    """Response body for workflow definition endpoints"""
    id: UUID
    name: str
    steps: list
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowExecuteRequest(BaseModel):
    """Request body for POST /workflows/execute"""
    definition_id: UUID
    input_payload: Optional[dict] = None


class WorkflowExecutionResponse(BaseModel):
    """Response body for workflow execution endpoints"""
    id: UUID
    definition_id: UUID
    state: str
    input_payload: Optional[dict]
    trace_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    error_msg: Optional[str]

    class Config:
        from_attributes = True