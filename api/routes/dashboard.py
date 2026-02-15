import zoneinfo
from datetime import datetime, timedelta, timezone

from dateutil.rrule import rrulestr
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.calendar import CalendarEvent
from api.models.note import Note
from api.models.task import Task
from api.utils.auth import get_current_user
from api.utils.timezone import resolve_today


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
async def get_today(db: AsyncSession = Depends(get_db), tz: str | None = Query(None)):
    today_start, today_end, local_date = resolve_today(tz)
    seven_days_ago = today_start - timedelta(days=7)
    user_tz = zoneinfo.ZoneInfo(tz) if tz else timezone.utc

    # Tasks due today or overdue
    task_result = await db.execute(
        select(Task)
        .where(
            (Task.status != "done") &
            (Task.due_date.isnot(None)) &
            (Task.due_date < today_end)
        )
        .order_by(Task.priority.desc(), Task.created_at)
        .limit(20)
    )
    tasks_due = list(task_result.scalars().all())

    # Events for today - with recurring event expansion
    events_out: list[tuple[datetime, str, datetime | None, bool, str]] = []  # (start_time, title, end_time, all_day, id)

    # Non-recurring TIMED events today
    timed_result = await db.execute(
        select(CalendarEvent)
        .where(
            CalendarEvent.rrule.is_(None),
            CalendarEvent.recurring_event_id.is_(None),
            CalendarEvent.all_day.is_(False),
            CalendarEvent.start_time >= today_start,
            CalendarEvent.start_time < today_end,
        )
    )
    for e in timed_result.scalars().all():
        events_out.append((_ensure_utc(e.start_time), e.title, e.end_time, e.all_day, e.id))

    # Non-recurring ALL-DAY events: widen range +-1 day, filter by local date
    allday_result = await db.execute(
        select(CalendarEvent)
        .where(
            CalendarEvent.rrule.is_(None),
            CalendarEvent.recurring_event_id.is_(None),
            CalendarEvent.all_day.is_(True),
            CalendarEvent.start_time >= today_start - timedelta(days=1),
            CalendarEvent.start_time < today_end + timedelta(days=1),
        )
    )
    for e in allday_result.scalars().all():
        st = _ensure_utc(e.start_time)
        if st.astimezone(user_tz).strftime("%Y-%m-%d") == local_date:
            events_out.append((st, e.title, e.end_time, e.all_day, e.id))

    # Recurring masters - expand their RRULEs
    masters_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.rrule.isnot(None),
            CalendarEvent.recurring_event_id.is_(None),
        )
    )
    masters = masters_result.scalars().all()

    # Exception instances: wider range for all-day edge cases, filter in Python
    exc_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.recurring_event_id.isnot(None),
            CalendarEvent.start_time >= today_start - timedelta(days=1),
            CalendarEvent.start_time < today_end + timedelta(days=1),
        )
    )
    exceptions = []
    for exc in exc_result.scalars().all():
        st = _ensure_utc(exc.start_time)
        if exc.all_day:
            if st.astimezone(user_tz).strftime("%Y-%m-%d") == local_date:
                exceptions.append(exc)
        else:
            if today_start <= st < today_end:
                exceptions.append(exc)

    exc_by_master: dict[str, dict[str, CalendarEvent]] = {}
    for exc in exceptions:
        if exc.recurring_event_id not in exc_by_master:
            exc_by_master[exc.recurring_event_id] = {}
        if exc.recurrence_id:
            exc_by_master[exc.recurring_event_id][exc.recurrence_id] = exc

    # Expand each master's RRULE
    for master in masters:
        try:
            duration = (master.end_time - master.start_time) if master.end_time else timedelta(hours=1)

            # Handle timezone-aware expansion
            orig_tz = None
            if master.original_timezone:
                try:
                    orig_tz = zoneinfo.ZoneInfo(master.original_timezone)
                except Exception:
                    pass

            if orig_tz:
                dtstart_utc = master.start_time
                if dtstart_utc.tzinfo is None:
                    dtstart_utc = dtstart_utc.replace(tzinfo=timezone.utc)
                dtstart_local = dtstart_utc.astimezone(orig_tz)
                rule = rrulestr(master.rrule, dtstart=dtstart_local)

                if master.all_day:
                    # Widen range for all-day, filter by local date
                    wide_start = (today_start - timedelta(days=1)).astimezone(orig_tz)
                    wide_end = (today_end + timedelta(days=1)).astimezone(orig_tz)
                    occurrences_local = rule.between(wide_start, wide_end, inc=True)
                    occurrences = [
                        occ.astimezone(timezone.utc) for occ in occurrences_local
                        if occ.astimezone(timezone.utc).astimezone(user_tz).strftime("%Y-%m-%d") == local_date
                    ]
                else:
                    local_start = today_start.astimezone(orig_tz)
                    local_end = today_end.astimezone(orig_tz)
                    occurrences_local = rule.between(local_start, local_end, inc=True)
                    # Exclude end boundary for timed events
                    occurrences = [
                        occ.astimezone(timezone.utc) for occ in occurrences_local
                        if occ.astimezone(timezone.utc) < today_end
                    ]
            else:
                dtstart = master.start_time
                if dtstart.tzinfo is None:
                    dtstart = dtstart.replace(tzinfo=timezone.utc)
                rule = rrulestr(master.rrule, dtstart=dtstart)

                if master.all_day:
                    wide_start = today_start - timedelta(days=1)
                    wide_end = today_end + timedelta(days=1)
                    raw_occurrences = rule.between(wide_start, wide_end, inc=True)
                    occurrences = [
                        occ for occ in raw_occurrences
                        if occ.astimezone(user_tz).strftime("%Y-%m-%d") == local_date
                    ]
                else:
                    raw_occurrences = rule.between(today_start, today_end, inc=True)
                    occurrences = [occ for occ in raw_occurrences if occ < today_end]

            master_exceptions = exc_by_master.get(master.id, {})

            for occ_dt in occurrences:
                occ_iso = occ_dt.isoformat()
                if occ_iso in master_exceptions:
                    exc_event = master_exceptions[occ_iso]
                    events_out.append((_ensure_utc(exc_event.start_time), exc_event.title, exc_event.end_time, exc_event.all_day, exc_event.id))
                else:
                    occ_end = occ_dt + duration
                    synthetic_id = f"{master.id}__rec__{occ_dt.strftime('%Y%m%dT%H%M%S')}"
                    events_out.append((occ_dt, master.title, occ_end, master.all_day, synthetic_id))
        except Exception:
            # If RRULE expansion fails, skip this master
            pass

    # Add any exceptions not already included (edge case: moved outside original date)
    included_ids = {e[4] for e in events_out}
    for exc in exceptions:
        if exc.id not in included_ids:
            events_out.append((_ensure_utc(exc.start_time), exc.title, exc.end_time, exc.all_day, exc.id))

    # Sort by start time and limit
    events_out.sort(key=lambda e: e[0])
    events_out = events_out[:10]

    # Convert to list of event-like objects for the response
    events = [
        type('Event', (), {'id': eid, 'title': title, 'start_time': start, 'end_time': end, 'all_day': all_day})()
        for start, title, end, all_day, eid in events_out
    ]

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
        date=local_date,
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
async def get_journal_data(db: AsyncSession = Depends(get_db), tz: str | None = Query(None)):
    """Get activity data for generating a daily journal entry."""
    today_start, today_end, local_date = resolve_today(tz)

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
        date=local_date,
        notes_created=[DashboardNote(id=n.id, title=n.title, updated_at=_ensure_utc(n.updated_at)) for n in notes_created],
        notes_updated=[DashboardNote(id=n.id, title=n.title, updated_at=_ensure_utc(n.updated_at)) for n in notes_updated],
        tasks_created=[DashboardTask(id=t.id, title=t.title, status=t.status, priority=t.priority, due_date=_ensure_utc(t.due_date), project_id=t.project_id) for t in tasks_created],
        tasks_completed=[DashboardTask(id=t.id, title=t.title, status=t.status, priority=t.priority, due_date=_ensure_utc(t.due_date), project_id=t.project_id) for t in tasks_completed],
        events=[DashboardEvent(id=e.id, title=e.title, start_time=_ensure_utc(e.start_time), end_time=_ensure_utc(e.end_time), all_day=e.all_day) for e in events],
    )
