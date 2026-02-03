import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from api.database import Base


def generate_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_task_id)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="open")  # open, in_progress, done
    priority = Column(String, default="medium")  # low, medium, high, urgent
    due_date = Column(DateTime, nullable=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    milestone_id = Column(String, ForeignKey("project_milestones.id", ondelete="SET NULL"), nullable=True)
    source_note_id = Column(String, ForeignKey("notes.id", ondelete="SET NULL"), nullable=True)
    calendar_event_id = Column(String, ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True)
    ai_suggested = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="tasks")
    milestone = relationship("ProjectMilestone", back_populates="tasks")
    checklist = relationship("TaskChecklist", back_populates="task", cascade="all, delete-orphan", order_by="TaskChecklist.position")
    notes = relationship("TaskNote", back_populates="task", cascade="all, delete-orphan")


class TaskChecklist(Base):
    __tablename__ = "task_checklists"

    id = Column(String, primary_key=True, default=lambda: f"check_{uuid.uuid4().hex[:8]}")
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    text = Column(String, nullable=False)
    is_checked = Column(Boolean, default=False)
    position = Column(Integer, default=0)

    task = relationship("Task", back_populates="checklist")


class TaskNote(Base):
    __tablename__ = "task_notes"

    id = Column(String, primary_key=True, default=lambda: f"tn_{uuid.uuid4().hex[:8]}")
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="notes")
