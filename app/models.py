"""
Database models - Personal Intelligence Hub.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Date, Time, JSON
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SAEnum("pending", "in_progress", "done", name="task_status"),
        default="pending",
        nullable=False,
    )
    priority = Column(
        SAEnum("low", "medium", "high", name="task_priority"),
        default="medium",
        nullable=False,
    )
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(
        SAEnum("upcoming", "completed", "cancelled", name="schedule_status"),
        default="upcoming",
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    history = Column(JSON, default=list)
