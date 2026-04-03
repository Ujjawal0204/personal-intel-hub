"""
Schedule Router - REST endpoints for schedule CRUD.
"""

import uuid
import logging
from datetime import date, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Schedule
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/schedules", tags=["schedules"])

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

class ScheduleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    event_date: date
    start_time: time
    end_time: time

class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[str] = None

def _to_dict(s: Schedule) -> dict:
    return {
        "id": str(s.id),
        "title": s.title,
        "description": s.description,
        "event_date": str(s.event_date),
        "start_time": str(s.start_time),
        "end_time": str(s.end_time),
        "status": s.status,
        "created_at": str(s.created_at),
        "updated_at": str(s.updated_at),
    }

@router.get("")
async def list_schedules(
    event_date: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    stmt = select(Schedule).order_by(Schedule.event_date, Schedule.start_time)
    if event_date:
        stmt = stmt.where(Schedule.event_date == date.fromisoformat(event_date))
    if status:
        stmt = stmt.where(Schedule.status == status)
    result = await db.execute(stmt)
    return [_to_dict(e) for e in result.scalars().all()]

@router.post("", status_code=201)
async def create_schedule(
    body: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    if body.end_time <= body.start_time:
        raise HTTPException(400, "end_time must be after start_time")
    event = Schedule(
        title=body.title,
        description=body.description,
        event_date=body.event_date,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _to_dict(event)

@router.get("/{event_id}")
async def get_schedule(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    event = await db.get(Schedule, uuid.UUID(event_id))
    if not event:
        raise HTTPException(404, "Event not found")
    return _to_dict(event)

@router.patch("/{event_id}")
async def update_schedule(
    event_id: str,
    body: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    event = await db.get(Schedule, uuid.UUID(event_id))
    if not event:
        raise HTTPException(404, "Event not found")
    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(event, key, value)
    await db.commit()
    await db.refresh(event)
    return _to_dict(event)

@router.delete("/{event_id}")
async def delete_schedule(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    event = await db.get(Schedule, uuid.UUID(event_id))
    if not event:
        raise HTTPException(404, "Event not found")
    await db.delete(event)
    await db.commit()
    return {"message": f"Event '{event.title}' deleted."}
