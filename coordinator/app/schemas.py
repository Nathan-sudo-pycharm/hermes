from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# --- Auth schemas ---

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    class Config:
        from_attributes = True


# --- Workflow schemas ---

class WorkflowStep(BaseModel):
    name: str
    timeout_seconds: int = 10
    max_retries: int = 3

class WorkflowDefinitionCreate(BaseModel):
    name: str
    steps: List[WorkflowStep]

class WorkflowDefinitionResponse(BaseModel):
    id: UUID
    name: str
    steps: list
    created_at: datetime
    class Config:
        from_attributes = True

class WorkflowExecuteRequest(BaseModel):
    definition_id: UUID
    input_payload: Optional[dict] = None

class TaskExecutionResponse(BaseModel):
    id: UUID
    step_name: str
    step_index: int
    state: str
    worker_id: Optional[str]
    attempt_number: int
    max_attempts: int
    duration_ms: Optional[int]
    error_msg: Optional[str]
    queued_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    class Config:
        from_attributes = True

class WorkflowExecutionResponse(BaseModel):
    id: UUID
    definition_id: UUID
    state: str
    input_payload: Optional[dict]
    trace_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    error_msg: Optional[str]
    tasks: List[TaskExecutionResponse] = []
    class Config:
        from_attributes = True