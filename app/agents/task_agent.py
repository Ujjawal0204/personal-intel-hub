from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Task
from app.database import AsyncSessionLocal
from app.config import settings
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)

async def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: str = "",
) -> dict:
    """Create a new task and persist it to the database."""
    due = None
    if due_date:
        try:
            due = datetime.fromisoformat(due_date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    if priority not in ("low", "medium", "high"):
        priority = "medium"

    async with AsyncSessionLocal() as db:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return {
            "message": f"Task '{title}' created with {priority} priority.",
            "id": str(task.id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
        }

async def list_tasks(
    status: str = "",
    priority: str = "",
) -> dict:
    """List tasks, optionally filtered by status or priority."""
    async with AsyncSessionLocal() as db:
        q = select(Task)
        if status and status in ("pending", "in_progress", "done"):
            q = q.where(Task.status == status)
        if priority and priority in ("low", "medium", "high"):
            q = q.where(Task.priority == priority)
        q = q.order_by(Task.created_at.desc()).limit(20)
        result = await db.execute(q)
        tasks = result.scalars().all()

        if not tasks:
            return {"message": "No tasks found.", "tasks": []}

        return {
            "message": f"Found {len(tasks)} task(s).",
            "tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                }
                for t in tasks
            ],
        }

async def update_task(
    task_id: str,
    title: str = "",
    description: str = "",
    status: str = "",
    priority: str = "",
) -> dict:
    """Update a task by its ID."""
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, uuid.UUID(task_id))
        if not task:
            return {"error": f"Task {task_id} not found."}

        if title:
            task.title = title
        if description:
            task.description = description
        if status and status in ("pending", "in_progress", "done"):
            task.status = status
        if priority and priority in ("low", "medium", "high"):
            task.priority = priority

        await db.commit()
        await db.refresh(task)
        return {
            "message": f"Task '{task.title}' updated.",
            "id": str(task.id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
        }

async def delete_task(task_id: str) -> dict:
    """Delete a task by its ID."""
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, uuid.UUID(task_id))
        if not task:
            return {"error": f"Task {task_id} not found."}
        title = task.title
        await db.delete(task)
        await db.commit()
        return {"message": f"Task '{title}' deleted."}

task_agent = Agent(
    name="task_agent",
    model=settings.gemini_model,
    description="Manages tasks - create, list, update status, and delete.",
    instruction="""You are a task management assistant.
Use your tools to create, list, update, and delete tasks based on the user's request.
Always confirm what action you took and summarise the result clearly.
When listing tasks, present them in a readable format with status and priority.
If a due date is mentioned, parse it into ISO format (YYYY-MM-DD).""",
    tools=[
        FunctionTool(func=create_task),
        FunctionTool(func=list_tasks),
        FunctionTool(func=update_task),
        FunctionTool(func=delete_task),
    ],
)
