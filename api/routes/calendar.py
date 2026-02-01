import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.calendar import CalendarEvent, NoteCalendarLink
from api.models.note import Note
from api.models.settings import UserSettings
from api.models.task import Task
from api.schemas.calendar import (
    CalDAVCalendarInfo,
    CalendarSettingsResponse,
    CalendarSettingsUpdate,
    CalendarSyncResult,
    EventCreate,
    EventList,
    EventResponse,
    EventUpdate,
    LinkedNoteRef,
    LinkedTaskRef,
)
from api.services.calendar_sync import caldav_sync_service
from api.utils.auth import get_current_user
from api.utils.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"], dependencies=[Depends(get_current_user)])


async def _load_caldav_settings(db: AsyncSession) -> dict:
    """Load all CalDAV-related settings from the DB into a dict."""
    keys = [
        "calendar_source", "calendar_sync_enabled",
        "selected_calendars", "calendar_sync_range_past_days",
        "calendar_sync_range_future_days",
        "caldav_server_url", "caldav_username", "caldav_password",
        "last_sync_at", "last_sync_error",
    ]
    result = await db.execute(
        select(UserSettings).where(UserSettings.key.in_(keys))
    )
    settings_map = {}
    for row in result.scalars().all():
        settings_map[row.key] = row.value

    # Parse selected_calendars from JSON
    if "selected_calendars" in settings_map:
        try:
            settings_map["selected_calendars"] = json.loads(settings_map["selected_calendars"])
        except (json.JSONDecodeError, TypeError):
            settings_map["selected_calendars"] = []
    else:
        settings_map["selected_calendars"] = []

    return settings_map


async def _upsert_setting(db: AsyncSession, key: str, value: str):
    """Insert or update a single user setting."""
    now = datetime.now(timezone.utc)
    result = await db.execute(select(UserSettings).where(UserSettings.key == key))
    existing = result.scalar_one_or_none()
    if existing:
        existing.value = value
        existing.updated_at = now
    else:
        db.add(UserSettings(key=key, value=value, updated_at=now))


async def _build_event_response(event: CalendarEvent, db: AsyncSession) -> EventResponse:
    """Build EventResponse with linked notes and tasks."""
    # Linked notes via note_calendar_links
    note_link_result = await db.execute(
        select(Note.id, Note.title)
        .join(NoteCalendarLink, NoteCalendarLink.note_id == Note.id)
        .where(NoteCalendarLink.event_id == event.id)
    )
    linked_notes = [LinkedNoteRef(id=row[0], title=row[1]) for row in note_link_result.fetchall()]

    # Linked tasks via tasks.calendar_event_id
    task_result = await db.execute(
        select(Task.id, Task.title, Task.status).where(Task.calendar_event_id == event.id)
    )
    linked_tasks = [LinkedTaskRef(id=row[0], title=row[1], status=row[2]) for row in task_result.fetchall()]

    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description or "",
        start_time=event.start_time,
        end_time=event.end_time,
        all_day=event.all_day,
        location=event.location or "",
        calendar_source=event.calendar_source or "local",
        calendar_id=event.calendar_id or "",
        synced_at=event.synced_at,
        linked_notes=linked_notes,
        linked_tasks=linked_tasks,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(body: EventCreate, db: AsyncSession = Depends(get_db)):
    event = CalendarEvent(
        title=body.title,
        description=body.description,
        start_time=body.start_time,
        end_time=body.end_time,
        all_day=body.all_day,
        location=body.location,
        calendar_source="local",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    await manager.broadcast("event_created", {"id": event.id, "title": event.title})

    # Push to CalDAV if enabled (non-blocking)
    try:
        settings_map = await _load_caldav_settings(db)
        if settings_map.get("calendar_source") == "caldav" and settings_map.get("caldav_password"):
            result = await caldav_sync_service.push_single_event(event, settings_map)
            if result and "href" in result:
                event.caldav_href = result["href"]
                event.etag = result.get("etag", "")
                event.external_id = event.id
                event.calendar_source = "caldav"
                event.synced_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(event)
            elif result and "error" in result:
                logger.warning("CalDAV push returned error for '%s': %s", event.title, result["error"])
            else:
                logger.warning("CalDAV push skipped for '%s': empty result (no selected calendars?)", event.title)
    except Exception:
        logger.exception("CalDAV push failed for new event (non-blocking)")

    return await _build_event_response(event, db)


@router.get("/events", response_model=EventList)
async def list_events(
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(CalendarEvent).order_by(CalendarEvent.start_time)
    if start:
        query = query.where(CalendarEvent.start_time >= start)
    if end:
        query = query.where(CalendarEvent.start_time <= end)

    from sqlalchemy import func
    count_query = select(func.count()).select_from(CalendarEvent)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    result = await db.execute(query.offset(offset).limit(limit))
    events = list(result.scalars().all())
    event_responses = [await _build_event_response(e, db) for e in events]
    return EventList(events=event_responses, total=total)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return await _build_event_response(event, db)


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(event_id: str, body: EventUpdate, db: AsyncSession = Depends(get_db)):
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    await manager.broadcast("event_updated", {"id": event.id, "title": event.title})

    # Push update to CalDAV if event has a remote href (non-blocking)
    if event.caldav_href:
        try:
            settings_map = await _load_caldav_settings(db)
            await caldav_sync_service.update_remote_event(event, settings_map)
        except Exception:
            logger.exception("CalDAV update failed for event (non-blocking)")

    return await _build_event_response(event, db)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    # Delete from CalDAV server first if it has a remote href (non-blocking)
    if event.caldav_href:
        try:
            settings_map = await _load_caldav_settings(db)
            await caldav_sync_service.delete_remote_event(event, settings_map)
        except Exception:
            logger.exception("CalDAV delete failed for event (non-blocking)")

    await db.delete(event)
    await db.commit()
    await manager.broadcast("event_deleted", {"id": event_id})


@router.get("/caldav/calendars", response_model=list[CalDAVCalendarInfo])
async def list_caldav_calendars(db: AsyncSession = Depends(get_db)):
    """Test CalDAV connection and return available calendars."""
    settings_map = await _load_caldav_settings(db)
    url = settings_map.get("caldav_server_url", "")
    username = settings_map.get("caldav_username", "")
    password = settings_map.get("caldav_password", "")

    if not url or not username or not password:
        raise HTTPException(status_code=400, detail="CalDAV credentials not configured")

    try:
        calendars = await caldav_sync_service.list_calendars(url, username, password)
        return [CalDAVCalendarInfo(**c) for c in calendars]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CalDAV connection failed: {e}")


@router.post("/sync", response_model=CalendarSyncResult)
async def sync_calendar(db: AsyncSession = Depends(get_db)):
    """Trigger full CalDAV sync."""
    settings_map = await _load_caldav_settings(db)

    if settings_map.get("calendar_source") != "caldav":
        return CalendarSyncResult(
            errors=["Calendar source is not set to CalDAV"],
            last_sync=datetime.now(timezone.utc).isoformat(),
        )

    result = await caldav_sync_service.full_sync(db, settings_map)

    # Store sync timestamp and error in settings
    await _upsert_setting(db, "last_sync_at", result.get("last_sync") or datetime.now(timezone.utc).isoformat())
    errors = result.get("errors", [])
    await _upsert_setting(db, "last_sync_error", errors[0] if errors else "")
    await db.commit()

    return CalendarSyncResult(**result)


@router.get("/settings", response_model=CalendarSettingsResponse)
async def get_calendar_settings(db: AsyncSession = Depends(get_db)):
    settings_map = await _load_caldav_settings(db)

    return CalendarSettingsResponse(
        calendar_source=settings_map.get("calendar_source", ""),
        sync_enabled=settings_map.get("calendar_sync_enabled", "false") == "true",
        selected_calendars=settings_map.get("selected_calendars", []),
        sync_range_past_days=int(settings_map.get("calendar_sync_range_past_days", "30")),
        sync_range_future_days=int(settings_map.get("calendar_sync_range_future_days", "90")),
        caldav_server_url=settings_map.get("caldav_server_url", ""),
        caldav_username=settings_map.get("caldav_username", ""),
        caldav_has_password=bool(settings_map.get("caldav_password", "")),
        last_sync_at=settings_map.get("last_sync_at"),
        last_sync_error=settings_map.get("last_sync_error") or None,
    )


@router.put("/settings", response_model=CalendarSettingsResponse)
async def update_calendar_settings(body: CalendarSettingsUpdate, db: AsyncSession = Depends(get_db)):
    updates = {}
    if body.calendar_source is not None:
        updates["calendar_source"] = body.calendar_source
    if body.sync_enabled is not None:
        updates["calendar_sync_enabled"] = "true" if body.sync_enabled else "false"
    if body.selected_calendars is not None:
        updates["selected_calendars"] = json.dumps(body.selected_calendars)
    if body.sync_range_past_days is not None:
        updates["calendar_sync_range_past_days"] = str(body.sync_range_past_days)
    if body.sync_range_future_days is not None:
        updates["calendar_sync_range_future_days"] = str(body.sync_range_future_days)
    if body.caldav_server_url is not None:
        updates["caldav_server_url"] = body.caldav_server_url
    if body.caldav_username is not None:
        updates["caldav_username"] = body.caldav_username
    if body.caldav_password is not None:
        updates["caldav_password"] = body.caldav_password

    for key, value in updates.items():
        await _upsert_setting(db, key, value)

    await db.commit()
    return await get_calendar_settings(db)
