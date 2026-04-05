from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db, AsyncSessionLocal
from app.models import Task, AgentSession
from app.config import settings
import uuid
import random
import asyncio
from fastapi.responses import JSONResponse
import traceback, logging

_QUERY_MAX_RETRIES = 3
_QUERY_RETRY_DELAY = 10

logger = logging.getLogger(__name__)
router = APIRouter()

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None

class QueryRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

_SCHEDULE_KEYWORDS = {
    "schedule", "event", "meeting", "appointment", "calendar", "book",
    "slot", "free time", "conflict", "agenda", "standup", "sync",
    "today", "tomorrow", "next week", "this week",
}
_TASK_KEYWORDS = {
    "task", "todo", "to-do", "to do", "work item", "priority",
    "assign", "backlog", "ticket", "bug", "feature", "deadline",
}

def _route(message: str) -> str:
    """Return 'schedule' or 'task' based on message keywords."""
    lc = message.lower()
    s = sum(1 for k in _SCHEDULE_KEYWORDS if k in lc)
    t = sum(1 for k in _TASK_KEYWORDS if k in lc)
    return "schedule" if s > t else "task"


@router.post("/query")
async def query_agent(
    request: QueryRequest,
    _: str = Depends(verify_api_key),
):
    try:
        from app.agents.coordinator import _run_agent_with_retry
        from app.agents.task_agent import task_agent
        from app.agents.schedule_agent import schedule_agent
        from datetime import date

        session_id = request.session_id or str(uuid.uuid4())
        history = []

        # Load history in a short-lived session before the agent runs
        if request.session_id:
            async with AsyncSessionLocal() as db:
                agent_session = await db.get(AgentSession, uuid.UUID(request.session_id))
                if agent_session and agent_session.history:
                    history = agent_session.history

        # Route in Python — no LLM call needed for coordination
        route = _route(request.message)
        agent = schedule_agent if route == "schedule" else task_agent
        today = date.today().isoformat()
        message_with_date = f"[Today is {today}] {request.message}"

        response_text = ""
        for attempt in range(_QUERY_MAX_RETRIES):
            try:
                response_text = await _run_agent_with_retry(agent, message_with_date)
                break
            except Exception as agent_err:
                error_str = str(agent_err).lower()
                if any(k in error_str for k in ["429", "rate", "quota", "resource_exhausted"]):
                    if attempt < _QUERY_MAX_RETRIES - 1:
                        delay = _QUERY_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 3)
                        logger.warning(f"Agent rate limited, retrying in {delay:.1f}s (attempt {attempt+1}/{_QUERY_MAX_RETRIES})")
                        await asyncio.sleep(delay)
                        continue
                    return JSONResponse(status_code=429, content={
                        "response": "Rate limit reached. Please wait about a minute and try again.",
                        "session_id": session_id,
                        "error_type": "rate_limit",
                    })
                if any(k in error_str for k in ["unavailable", "503"]):
                    return JSONResponse(status_code=503, content={
                        "response": "AI service temporarily unavailable. Please try again shortly.",
                        "session_id": session_id,
                        "error_type": "service_unavailable",
                    })
                raise

        if not response_text:
            response_text = "I processed your request but have no additional information to share."

        now = datetime.utcnow().isoformat()
        history.append({"user": request.message, "assistant": response_text, "timestamp": now})

        # Save history in a fresh short-lived session after the agent finishes
        async with AsyncSessionLocal() as db:
            agent_session = await db.get(AgentSession, uuid.UUID(session_id))
            if agent_session:
                agent_session.history = history
            else:
                agent_session = AgentSession(id=uuid.UUID(session_id), history=history)
                db.add(agent_session)
            await db.commit()

        return {"response": response_text, "session_id": session_id}

    except Exception as e:
        error_message = str(e).lower()
        logger.error(f"Query error: {e}\n{traceback.format_exc()}")

        if any(k in error_message for k in ["429", "resource_exhausted", "rate limit", "quota"]):
            return JSONResponse(status_code=429, content={
                "response": "Gemini API rate limit reached. Please wait a moment.",
                "session_id": request.session_id,
                "error_type": "rate_limit",
            })
        if any(k in error_message for k in ["401", "403", "api_key", "unauthorized"]):
            return JSONResponse(status_code=503, content={
                "response": "AI service authentication error. Check API key.",
                "session_id": request.session_id,
                "error_type": "auth_error",
            })
        return JSONResponse(status_code=500, content={
            "response": f"Error: {str(e)[:200]}",
            "session_id": request.session_id,
            "error_type": "internal_error",
        })

@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    q = select(Task).order_by(Task.created_at.desc())
    if status:
        q = q.where(Task.status == status)
    if priority:
        q = q.where(Task.priority == priority)
    result = await db.execute(q)
    tasks = result.scalars().all()
    return [_task_dict(t) for t in tasks]

@router.post("/tasks", status_code=201)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    task = Task(**body.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)

@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    task = await db.get(Task, uuid.UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_dict(task)

@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    task = await db.get(Task, uuid.UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    task = await db.get(Task, uuid.UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
    return {"message": f"Task '{task.title}' deleted."}

def _task_dict(t: Task) -> dict:
    return {
        "id": str(t.id),
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "due_date": str(t.due_date) if t.due_date else None,
        "created_at": str(t.created_at),
        "updated_at": str(t.updated_at),
    }
