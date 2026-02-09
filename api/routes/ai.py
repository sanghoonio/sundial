import zoneinfo
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.calendar import CalendarEvent
from api.models.note import Note
from api.models.task import Task
from api.services import ai_service
from api.services.block_parser import extract_markdown_text
from api.utils.auth import get_current_user
from api.utils.timezone import resolve_today

router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(get_current_user)])


class ChatRequest(BaseModel):
    message: str
    note_id: str | None = None
    context: str | None = None


class ChatResponse(BaseModel):
    response: str = ""
    error: str = ""


class DailySuggestionsResponse(BaseModel):
    summary: str = ""
    priorities: list[str] = []
    connections: list[str] = []


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Build context from note if note_id provided
    context = body.context
    if body.note_id and not context:
        result = await db.execute(select(Note).where(Note.id == body.note_id))
        note = result.scalar_one_or_none()
        if note and note.content:
            context = f"Title: {note.title}\n\n{extract_markdown_text(note.content)}"

    result = await ai_service.chat(body.message, note_id=body.note_id, context=context, db=db)

    if "error" in result:
        return ChatResponse(error=result["error"])
    return ChatResponse(response=result.get("response", ""))


class AnalyzeNoteResponse(BaseModel):
    suggested_tags: list[str] = []
    extracted_tasks: list[dict] = []
    linked_events: list[str] = []


@router.post("/analyze-note/{note_id}", response_model=AnalyzeNoteResponse)
async def analyze_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger AI analysis (auto-tag, extract tasks, link events) for a note.

    Returns synchronous results for immediate UI feedback.
    """
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if not note.content:
        return AnalyzeNoteResponse()

    from api.models.note import Tag
    from api.services.block_parser import extract_markdown_text

    content = extract_markdown_text(note.content)
    if not content.strip():
        return AnalyzeNoteResponse()

    # Get existing tags in system
    tag_result = await db.execute(select(Tag.name))
    existing_tags = [row[0] for row in tag_result.fetchall()]

    # Run auto-tag
    suggested_tags = await ai_service.auto_tag(content, existing_tags, db)

    # Run task extraction
    extracted_tasks = await ai_service.extract_tasks(content, note.title, db)

    # Run event linking
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    end = now + timedelta(days=30)
    event_result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.start_time.between(start, end))
        .limit(50)
    )
    events_raw = event_result.scalars().all()
    events = [
        {"id": e.id, "title": e.title, "description": e.description or "", "start_time": str(e.start_time)}
        for e in events_raw
    ]
    linked_events = await ai_service.link_events(content, events, db) if events else []

    return AnalyzeNoteResponse(
        suggested_tags=suggested_tags,
        extracted_tasks=extracted_tasks,
        linked_events=linked_events,
    )


@router.get("/suggestions/daily", response_model=DailySuggestionsResponse)
async def daily_suggestions(db: AsyncSession = Depends(get_db), tz: str | None = Query(None)):
    today_start, today_end, local_date = resolve_today(tz)
    seven_days_ago = today_start - timedelta(days=7)

    # Resolve user timezone for display conversion
    user_tz = zoneinfo.ZoneInfo(tz) if tz else timezone.utc

    # Today's events — convert times to user's local timezone
    event_result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.start_time.between(today_start, today_end))
        .order_by(CalendarEvent.start_time)
        .limit(20)
    )
    events = [
        {
            "id": e.id,
            "title": e.title,
            "start_time": e.start_time.replace(tzinfo=timezone.utc).astimezone(user_tz).isoformat(),
            "end_time": e.end_time.replace(tzinfo=timezone.utc).astimezone(user_tz).isoformat() if e.end_time else None,
        }
        for e in event_result.scalars().all()
    ]

    # Pending tasks — convert due_date to user's local timezone
    task_result = await db.execute(
        select(Task)
        .where(Task.status != "done")
        .order_by(Task.priority.desc(), Task.created_at)
        .limit(20)
    )
    tasks = [
        {
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "due_date": t.due_date.replace(tzinfo=timezone.utc).astimezone(user_tz).isoformat() if t.due_date else None,
        }
        for t in task_result.scalars().all()
    ]

    # Recent notes
    note_result = await db.execute(
        select(Note)
        .where(Note.updated_at >= seven_days_ago)
        .order_by(Note.updated_at.desc())
        .limit(10)
    )
    notes = [
        {"id": n.id, "title": n.title}
        for n in note_result.scalars().all()
    ]

    result = await ai_service.daily_suggestions(events, tasks, notes, db, tz=tz, local_date=local_date)
    return DailySuggestionsResponse(**result)
