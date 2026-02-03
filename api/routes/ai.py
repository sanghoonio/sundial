from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
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


@router.post("/analyze-note/{note_id}")
async def analyze_note(
    note_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger AI analysis (auto-tag, extract tasks, link events) for a note."""
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    from api.services.ai_background import process_note_ai
    background_tasks.add_task(process_note_ai, note_id)

    return {"status": "queued", "note_id": note_id}


@router.get("/suggestions/daily", response_model=DailySuggestionsResponse)
async def daily_suggestions(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    seven_days_ago = today_start - timedelta(days=7)

    # Today's events
    event_result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.start_time.between(today_start, today_end))
        .order_by(CalendarEvent.start_time)
        .limit(20)
    )
    events = [
        {"id": e.id, "title": e.title, "start_time": str(e.start_time), "end_time": str(e.end_time)}
        for e in event_result.scalars().all()
    ]

    # Pending tasks
    task_result = await db.execute(
        select(Task)
        .where(Task.status != "done")
        .order_by(Task.priority.desc(), Task.created_at)
        .limit(20)
    )
    tasks = [
        {"id": t.id, "title": t.title, "priority": t.priority, "due_date": str(t.due_date) if t.due_date else None}
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

    result = await ai_service.daily_suggestions(events, tasks, notes, db)
    return DailySuggestionsResponse(**result)
