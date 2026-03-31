from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models import Task, TaskStatus, TaskPriority
from app.agents.coordinator import run_coordinator
from app.config import settings
import uuid
from fastapi.responses import JSONResponse
import traceback, logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Auth dependency ───────────────────────────────────────────────────────────

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.medium
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class QueryRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    session_id: str

# ── Natural language query endpoint ──────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query_agent(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    try:
        session_id = request.session_id or str(uuid.uuid4())
        response = await run_coordinator(request.message, session_id, db)
        return {"response": response, "session_id": session_id}

    except Exception as e:
        error_message = str(e).lower()
        logger.error(f"Query error: {e}\n{traceback.format_exc()}")

        if any(k in error_message for k in [
            "429", "resource_exhausted", "rate limit", "quota",
            "too many requests", "resourceexhausted"
        ]):
            return JSONResponse(status_code=429, content={
                "response": "⚠️ Gemini API rate limit reached. Please wait a moment and try again.",
                "session_id": request.session_id,
                "error_type": "rate_limit",
            })

        if any(k in error_message for k in ["401", "403", "api_key", "unauthorized"]):
            return JSONResponse(status_code=503, content={
                "response": "⚠️ AI service authentication error. Check API key.",
                "session_id": request.session_id,
                "error_type": "auth_error",
            })

        return JSONResponse(status_code=500, content={
            "response": f"⚠️ Error: {str(e)[:200]}",
            "session_id": request.session_id,
            "error_type": "internal_error",
        })

# ── Direct CRUD endpoints ─────────────────────────────────────────────────────

@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    q = select(Task).order_by(Task.created_at.desc())
    if status:
        q = q.where(Task.status == status)
    if priority:
        q = q.where(Task.priority == priority)
    result = await db.execute(q)
    return result.scalars().all()

@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    task = Task(id=str(uuid.uuid4()), **body.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
