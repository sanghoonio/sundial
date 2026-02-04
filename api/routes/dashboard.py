from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.calendar import CalendarEvent
from api.models.note import Note
from api.models.task import Task
from api.utils.auth import get_current_user


class DashboardEvent(BaseModel):
    id: str
    title: str
    start_time: datetime
    end_time: datetime | None
    all_day: bool

    model_config = {"from_attributes": True}


class DashboardTask(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    due_date: datetime | None
    project_id: str

    model_config = {"from_attributes": True}


class DashboardNote(BaseModel):
    id: str
    title: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    date: str
    calendar_events: list[DashboardEvent]
    tasks_due: list[DashboardTask]
    tasks_linked_to_events: list[DashboardTask]
    recent_notes: list[DashboardNote]
    suggestions: list = []


class JournalDataResponse(BaseModel):
    date: str
    notes_created: list[DashboardNote]
    notes_updated: list[DashboardNote]
    tasks_created: list[DashboardTask]
    tasks_completed: list[DashboardTask]
    events: list[DashboardEvent]


router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure datetime is UTC-aware for consistent frontend parsing."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/today", response_model=DashboardResponse)
async def get_today(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    seven_days_ago = today_start - timedelta(days=7)

    # Tasks due today or overdue
    task_result = await db.execute(
        select(Task)
        .where(
            (Task.status != "done") &
            (Task.due_date.isnot(None)) &
            (Task.due_date <= today_end)
        )
        .order_by(Task.priority.desc(), Task.created_at)
        .limit(20)
    )
    tasks_due = list(task_result.scalars().all())

    # Events for today
    event_result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.start_time.between(today_start, today_end))
        .order_by(CalendarEvent.start_time)
        .limit(10)
    )
    events = list(event_result.scalars().all())

    # Tasks linked to today's events
    event_ids = [e.id for e in events]
    tasks_linked = []
    if event_ids:
        linked_result = await db.execute(
            select(Task).where(Task.calendar_event_id.in_(event_ids))
        )
        tasks_linked = list(linked_result.scalars().all())

    # Recent notes (last 7 days)
    note_result = await db.execute(
        select(Note)
        .where(Note.updated_at >= seven_days_ago)
        .order_by(Note.updated_at.desc())
        .limit(10)
    )
    notes = list(note_result.scalars().all())

    return DashboardResponse(
        date=today_start.strftime("%Y-%m-%d"),
        calendar_events=[DashboardEvent(
            id=e.id, title=e.title, start_time=_ensure_utc(e.start_time), end_time=_ensure_utc(e.end_time), all_day=e.all_day,
        ) for e in events],
        tasks_due=[DashboardTask(
            id=t.id, title=t.title, status=t.status, priority=t.priority, due_date=_ensure_utc(t.due_date), project_id=t.project_id,
        ) for t in tasks_due],
        tasks_linked_to_events=[DashboardTask(
            id=t.id, title=t.title, status=t.status, priority=t.priority, due_date=_ensure_utc(t.due_date), project_id=t.project_id,
        ) for t in tasks_linked],
        recent_notes=[DashboardNote(
            id=n.id, title=n.title, updated_at=_ensure_utc(n.updated_at),
        ) for n in notes],
        suggestions=[],
    )


@router.get("/journal-data", response_model=JournalDataResponse)
async def get_journal_data(db: AsyncSession = Depends(get_db)):
    """Get activity data for generating a daily journal entry."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Notes created today
    notes_created_result = await db.execute(
        select(Note)
        .where(Note.created_at.between(today_start, today_end))
        .order_by(Note.created_at.desc())
    )
    notes_created = list(notes_created_result.scalars().all())
    notes_created_ids = {n.id for n in notes_created}

    # Notes updated today (excluding those created today)
    notes_updated_result = await db.execute(
        select(Note)
        .where(
            Note.updated_at.between(today_start, today_end),
            ~Note.id.in_(notes_created_ids) if notes_created_ids else True,
        )
        .order_by(Note.updated_at.desc())
    )
    notes_updated = list(notes_updated_result.scalars().all())

    # Tasks created today
    tasks_created_result = await db.execute(
        select(Task)
        .where(Task.created_at.between(today_start, today_end))
        .order_by(Task.created_at.desc())
    )
    tasks_created = list(tasks_created_result.scalars().all())

    # Tasks completed today
    tasks_completed_result = await db.execute(
        select(Task)
        .where(Task.completed_at.between(today_start, today_end))
        .order_by(Task.completed_at.desc())
    )
    tasks_completed = list(tasks_completed_result.scalars().all())

    # Events that occurred today
    events_result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.start_time.between(today_start, today_end))
        .order_by(CalendarEvent.start_time)
    )
    events = list(events_result.scalars().all())

    return JournalDataResponse(
        date=today_start.strftime("%Y-%m-%d"),
        notes_created=[DashboardNote(id=n.id, title=n.title, updated_at=_ensure_utc(n.updated_at)) for n in notes_created],
        notes_updated=[DashboardNote(id=n.id, title=n.title, updated_at=_ensure_utc(n.updated_at)) for n in notes_updated],
        tasks_created=[DashboardTask(id=t.id, title=t.title, status=t.status, priority=t.priority, due_date=_ensure_utc(t.due_date), project_id=t.project_id) for t in tasks_created],
        tasks_completed=[DashboardTask(id=t.id, title=t.title, status=t.status, priority=t.priority, due_date=_ensure_utc(t.due_date), project_id=t.project_id) for t in tasks_completed],
        events=[DashboardEvent(id=e.id, title=e.title, start_time=_ensure_utc(e.start_time), end_time=_ensure_utc(e.end_time), all_day=e.all_day) for e in events],
    )
