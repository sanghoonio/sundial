import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.calendar import CalendarEvent
from api.models.settings import UserSettings
from api.schemas.calendar import (
    CalendarSettingsResponse,
    CalendarSettingsUpdate,
    EventCreate,
    EventList,
    EventResponse,
    EventUpdate,
)
from api.utils.auth import get_current_user
from api.utils.websocket import manager

router = APIRouter(prefix="/calendar", tags=["calendar"], dependencies=[Depends(get_current_user)])


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
    return event


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
    return EventList(events=events, total=total)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


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
    return event


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(event)
    await db.commit()
    await manager.broadcast("event_deleted", {"id": event_id})


@router.post("/sync")
async def sync_calendar(db: AsyncSession = Depends(get_db)):
    """Stub: trigger calendar synchronization."""
    return {
        "synced_events": 0,
        "created": 0,
        "updated": 0,
        "deleted": 0,
        "last_sync": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/settings", response_model=CalendarSettingsResponse)
async def get_calendar_settings(db: AsyncSession = Depends(get_db)):
    settings_map = {}
    result = await db.execute(
        select(UserSettings).where(
            UserSettings.key.in_([
                "calendar_source", "calendar_sync_enabled",
                "selected_calendars", "calendar_sync_range_past_days",
                "calendar_sync_range_future_days",
            ])
        )
    )
    for row in result.scalars().all():
        settings_map[row.key] = row.value

    selected = []
    if "selected_calendars" in settings_map:
        try:
            selected = json.loads(settings_map["selected_calendars"])
        except (json.JSONDecodeError, TypeError):
            selected = []

    return CalendarSettingsResponse(
        calendar_source=settings_map.get("calendar_source", ""),
        sync_enabled=settings_map.get("calendar_sync_enabled", "false") == "true",
        selected_calendars=selected,
        sync_range_past_days=int(settings_map.get("calendar_sync_range_past_days", "30")),
        sync_range_future_days=int(settings_map.get("calendar_sync_range_future_days", "90")),
    )


@router.put("/settings", response_model=CalendarSettingsResponse)
async def update_calendar_settings(body: CalendarSettingsUpdate, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
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

    for key, value in updates.items():
        result = await db.execute(select(UserSettings).where(UserSettings.key == key))
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
            existing.updated_at = now
        else:
            db.add(UserSettings(key=key, value=value, updated_at=now))

    await db.commit()
    return await get_calendar_settings(db)
