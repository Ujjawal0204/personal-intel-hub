from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models import Task, TaskStatus, TaskPriority
from app.config import settings
from datetime import datetime, timezone
import uuid

# ── Tools (plain async functions ADK wraps automatically) ─────────────────────

async def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: str = "",
    db: AsyncSession = None,
) -> dict:
    """Create a new task and persist it to the database."""
    due = None
    if due_date:
        try:
            due = datetime.fromisoformat(due_date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    task = Task(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        priority=TaskPriority(priority) if priority in TaskPriority._value2member_map_ else TaskPriority.medium,
        due_date=due,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {"id": task.id, "title": task.title, "status": task.status, "priority": task.priority}

async def list_tasks(
    status: str = "",
    priority: str = "",
    db: AsyncSession = None,
) -> list[dict]:
    """List tasks, optionally filtered by status or priority."""
    q = select(Task)
    if status and status in TaskStatus._value2member_map_:
        q = q.where(Task.status == TaskStatus(status))
    if priority and priority in TaskPriority._value2member_map_:
        q = q.where(Task.priority == TaskPriority(priority))
    q = q.order_by(Task.created_at.desc()).limit(20)
    result = await db.execute(q)
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        }
        for t in tasks
    ]

async def update_task_status(
    task_id: str,
    status: str,
    db: AsyncSession = None,
) -> dict:
    """Update the status of a task by its ID."""
    if status not in TaskStatus._value2member_map_:
        return {"error": f"Invalid status '{status}'. Use: pending, in_progress, done"}
    await db.execute(
        update(Task)
        .where(Task.id == task_id)
        .values(status=TaskStatus(status), updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"task_id": task_id, "new_status": status}

async def delete_task(task_id: str, db: AsyncSession = None) -> dict:
    """Delete a task by its ID."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return {"error": f"Task {task_id} not found"}
    await db.delete(task)
    await db.commit()
    return {"deleted": task_id}

# ── Agent factory ─────────────────────────────────────────────────────────────

def build_task_agent(db: AsyncSession) -> Agent:
    """Return a task agent with db-bound tools."""

    async def _create(title: str, description: str = "", priority: str = "medium", due_date: str = "") -> dict:
        return await create_task(title, description, priority, due_date, db=db)

    async def _list(status: str = "", priority: str = "") -> list[dict]:
        return await list_tasks(status, priority, db=db)

    async def _update_status(task_id: str, status: str) -> dict:
        return await update_task_status(task_id, status, db=db)

    async def _delete(task_id: str) -> dict:
        return await delete_task(task_id, db=db)

    return Agent(
        name="task_agent",
        model=settings.gemini_model,
        description="Manages tasks — create, list, update status, and delete.",
        instruction="""You are a task management assistant.
Use your tools to create, list, update, and delete tasks based on the user's request.
Always confirm what action you took and summarise the result clearly.
When listing tasks, present them in a readable format with status and priority.
If a due date is mentioned, parse it into ISO format (YYYY-MM-DD).""",
        tools=[
            FunctionTool(_create),
            FunctionTool(_list),
            FunctionTool(_update_status),
            FunctionTool(_delete),
        ],
    )
