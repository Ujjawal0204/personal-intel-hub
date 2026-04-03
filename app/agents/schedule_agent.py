"""
Schedule Agent - manages calendar events via natural language.
"""

import uuid
import logging
from datetime import datetime, date, time, timedelta

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from sqlalchemy import select, and_

from app.database import AsyncSessionLocal
from app.models import Schedule
from app.config import settings

logger = logging.getLogger(__name__)


async def create_schedule(
    title: str,
    event_date: str,
    start_time: str,
    end_time: str,
    description: str = "",
) -> dict:
    """
    Create a new schedule event.

    Args:
        title: Name of the event
        event_date: Date in YYYY-MM-DD format
        start_time: Start time in HH:MM format (24h)
        end_time: End time in HH:MM format (24h)
        description: Optional details about the event
    """
    try:
        parsed_date = date.fromisoformat(event_date)
        parsed_start = time.fromisoformat(start_time)
        parsed_end = time.fromisoformat(end_time)

        if parsed_end <= parsed_start:
            return {"error": "end_time must be after start_time"}

        async with AsyncSessionLocal() as db:
            stmt = select(Schedule).where(
                and_(
                    Schedule.event_date == parsed_date,
                    Schedule.status != "cancelled",
                    Schedule.start_time < parsed_end,
                    Schedule.end_time > parsed_start,
                )
            )
            result = await db.execute(stmt)
            conflicts = result.scalars().all()

            conflict_warning = ""
            if conflicts:
                titles = [c.title for c in conflicts]
                conflict_warning = f" Warning: This overlaps with: {', '.join(titles)}"

            event = Schedule(
                title=title,
                description=description,
                event_date=parsed_date,
                start_time=parsed_start,
                end_time=parsed_end,
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)

            return {
                "message": f"Event '{title}' created for {event_date} ({start_time}-{end_time}).{conflict_warning}",
                "event": {
                    "id": str(event.id),
                    "title": event.title,
                    "event_date": str(event.event_date),
                    "start_time": str(event.start_time),
                    "end_time": str(event.end_time),
                    "status": event.status,
                },
            }
    except ValueError as e:
        return {"error": f"Invalid date/time format: {e}"}
    except Exception as e:
        logger.error(f"create_schedule error: {e}")
        return {"error": str(e)}


async def list_schedules(
    event_date: str = "",
    status: str = "",
) -> dict:
    """
    List schedule events, optionally filtered by date or status.

    Args:
        event_date: Optional date filter (YYYY-MM-DD). Leave empty for all.
        status: Optional status filter (upcoming/completed/cancelled). Leave empty for all.
    """
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Schedule).order_by(Schedule.event_date, Schedule.start_time)
            if event_date:
                stmt = stmt.where(Schedule.event_date == date.fromisoformat(event_date))
            if status:
                stmt = stmt.where(Schedule.status == status)

            result = await db.execute(stmt)
            events = result.scalars().all()

            if not events:
                return {"message": "No events found.", "events": []}

            return {
                "message": f"Found {len(events)} event(s).",
                "events": [
                    {
                        "id": str(e.id),
                        "title": e.title,
                        "description": e.description or "",
                        "event_date": str(e.event_date),
                        "start_time": str(e.start_time),
                        "end_time": str(e.end_time),
                        "status": e.status,
                    }
                    for e in events
                ],
            }
    except Exception as e:
        logger.error(f"list_schedules error: {e}")
        return {"error": str(e)}


async def update_schedule(
    event_id: str,
    title: str = "",
    event_date: str = "",
    start_time: str = "",
    end_time: str = "",
    description: str = "",
    status: str = "",
) -> dict:
    """
    Update an existing schedule event by ID.

    Args:
        event_id: UUID of the event to update.
        title: New title (leave empty to keep current).
        event_date: New date YYYY-MM-DD (leave empty to keep current).
        start_time: New start HH:MM (leave empty to keep current).
        end_time: New end HH:MM (leave empty to keep current).
        description: New description (leave empty to keep current).
        status: New status - upcoming/completed/cancelled (leave empty to keep current).
    """
    try:
        async with AsyncSessionLocal() as db:
            event = await db.get(Schedule, uuid.UUID(event_id))
            if not event:
                return {"error": f"Event {event_id} not found."}

            if title:
                event.title = title
            if description:
                event.description = description
            if event_date:
                event.event_date = date.fromisoformat(event_date)
            if start_time:
                event.start_time = time.fromisoformat(start_time)
            if end_time:
                event.end_time = time.fromisoformat(end_time)
            if status:
                event.status = status

            await db.commit()
            await db.refresh(event)

            return {
                "message": f"Event '{event.title}' updated.",
                "event": {
                    "id": str(event.id),
                    "title": event.title,
                    "event_date": str(event.event_date),
                    "start_time": str(event.start_time),
                    "end_time": str(event.end_time),
                    "status": event.status,
                },
            }
    except Exception as e:
        logger.error(f"update_schedule error: {e}")
        return {"error": str(e)}


async def delete_schedule(event_id: str) -> dict:
    """
    Delete a schedule event by ID.

    Args:
        event_id: UUID of the event to delete.
    """
    try:
        async with AsyncSessionLocal() as db:
            event = await db.get(Schedule, uuid.UUID(event_id))
            if not event:
                return {"error": f"Event {event_id} not found."}

            title = event.title
            await db.delete(event)
            await db.commit()
            return {"message": f"Event '{title}' deleted."}
    except Exception as e:
        logger.error(f"delete_schedule error: {e}")
        return {"error": str(e)}


async def get_daily_summary(event_date: str = "") -> dict:
    """
    Get a summary of all events for a given day. Defaults to today.

    Args:
        event_date: Date in YYYY-MM-DD format. Leave empty for today.
    """
    try:
        target_date = date.fromisoformat(event_date) if event_date else date.today()

        async with AsyncSessionLocal() as db:
            stmt = (
                select(Schedule)
                .where(
                    and_(
                        Schedule.event_date == target_date,
                        Schedule.status != "cancelled",
                    )
                )
                .order_by(Schedule.start_time)
            )
            result = await db.execute(stmt)
            events = result.scalars().all()

            if not events:
                return {
                    "message": f"No events scheduled for {target_date}. Your day is free!",
                    "date": str(target_date),
                    "total_events": 0,
                    "events": [],
                }

            total_minutes = sum(
                (
                    datetime.combine(target_date, e.end_time)
                    - datetime.combine(target_date, e.start_time)
                ).seconds / 60
                for e in events
            )

            return {
                "message": f"You have {len(events)} event(s) on {target_date}, totalling {total_minutes:.0f} minutes.",
                "date": str(target_date),
                "total_events": len(events),
                "total_minutes": total_minutes,
                "events": [
                    {
                        "title": e.title,
                        "time": f"{e.start_time.strftime('%H:%M')}-{e.end_time.strftime('%H:%M')}",
                        "status": e.status,
                    }
                    for e in events
                ],
            }
    except Exception as e:
        logger.error(f"get_daily_summary error: {e}")
        return {"error": str(e)}


schedule_agent = Agent(
    name="schedule_agent",
    model=settings.gemini_model,
    description="Manages calendar events - create, list, update, delete, and daily summaries.",
    instruction=f"""Today's date is {date.today().isoformat()}. You are the Schedule Agent, a specialist in managing calendar events and schedules.

You can:
- Create events with date, start time, end time, and description
- List and filter events by date or status
- Update event details or mark them completed/cancelled
- Delete events
- Provide daily summaries showing total events and time booked
- Automatically detect scheduling conflicts when creating events

When the user asks about schedules, events, meetings, appointments, or calendar-related topics, use the appropriate tool.
Always confirm actions with clear, friendly responses.
Format times in 24-hour format (HH:MM) and dates as YYYY-MM-DD.""",
    tools=[
        FunctionTool(func=create_schedule),
        FunctionTool(func=list_schedules),
        FunctionTool(func=update_schedule),
        FunctionTool(func=delete_schedule),
        FunctionTool(func=get_daily_summary),
    ],
)

