import json
import logging
from datetime import datetime, timedelta, timezone

import zoneinfo
from dateutil.rrule import rrulestr
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
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
from api.utils.websocket import get_client_id, manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"], dependencies=[Depends(get_current_user)])


async def _load_caldav_settings(db: AsyncSession) -> dict:
    """Load all CalDAV-related settings from the DB into a dict."""
    keys = [
        "calendar_source", "calendar_sync_enabled",
        "selected_calendars", "calendar_sync_range_past_days",
        "calendar_sync_range_future_days", "calendar_sync_interval_minutes",
        "calendar_sync_direction",
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

    # Ensure all datetimes are UTC-aware for consistent frontend parsing
    def ensure_utc_aware(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description or "",
        start_time=ensure_utc_aware(event.start_time),
        end_time=ensure_utc_aware(event.end_time),
        all_day=event.all_day,
        location=event.location or "",
        calendar_source=event.calendar_source or "local",
        calendar_id=event.calendar_id or "",
        rrule=event.rrule,
        recurring_event_id=event.recurring_event_id,
        recurrence_id=event.recurrence_id,
        synced_at=ensure_utc_aware(event.synced_at),
        linked_notes=linked_notes,
        linked_tasks=linked_tasks,
        created_at=ensure_utc_aware(event.created_at),
        updated_at=ensure_utc_aware(event.updated_at),
    )


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Convert datetime to UTC. Naive datetimes are assumed to be UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(body: EventCreate, db: AsyncSession = Depends(get_db), client_id: str | None = Depends(get_client_id)):
    event = CalendarEvent(
        title=body.title,
        description=body.description,
        start_time=_ensure_utc(body.start_time),
        end_time=_ensure_utc(body.end_time),
        all_day=body.all_day,
        location=body.location,
        rrule=body.rrule,
        calendar_source="local",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    await manager.broadcast("event_created", {"id": event.id, "title": event.title}, exclude_client_id=client_id)

    # Push to CalDAV if enabled and direction allows export (non-blocking)
    try:
        settings_map = await _load_caldav_settings(db)
        direction = settings_map.get("calendar_sync_direction", "import")
        if (settings_map.get("calendar_source") == "caldav"
                and settings_map.get("caldav_password")
                and direction in ("both", "export")):
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
    limit: int = Query(500, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # 1. Non-recurring events (no rrule) and non-exception events in range
    query = select(CalendarEvent).where(
        CalendarEvent.rrule.is_(None),
        CalendarEvent.recurring_event_id.is_(None),
    ).order_by(CalendarEvent.start_time)
    if start:
        query = query.where(CalendarEvent.start_time >= start)
    if end:
        query = query.where(CalendarEvent.start_time < end + timedelta(days=1))

    result = await db.execute(query)
    non_recurring = list(result.scalars().all())
    event_responses = [await _build_event_response(e, db) for e in non_recurring]

    # 2. Recurring masters (rrule IS NOT NULL, recurring_event_id IS NULL)
    master_query = select(CalendarEvent).where(
        CalendarEvent.rrule.isnot(None),
        CalendarEvent.recurring_event_id.is_(None),
    )
    master_result = await db.execute(master_query)
    masters = list(master_result.scalars().all())

    # 3. Exception instances in the range
    exc_query = select(CalendarEvent).where(
        CalendarEvent.recurring_event_id.isnot(None),
    )
    if start:
        exc_query = exc_query.where(CalendarEvent.start_time >= start)
    if end:
        exc_query = exc_query.where(CalendarEvent.start_time < end + timedelta(days=1))
    exc_result = await db.execute(exc_query)
    exceptions = list(exc_result.scalars().all())

    # Build a map of exception dates per master for override matching
    exc_by_master: dict[str, dict[str, CalendarEvent]] = {}
    for exc in exceptions:
        master_id = exc.recurring_event_id
        if master_id not in exc_by_master:
            exc_by_master[master_id] = {}
        if exc.recurrence_id:
            exc_by_master[master_id][exc.recurrence_id] = exc

    # 4. Expand each master's RRULE into virtual instances
    # Ensure range bounds are timezone-aware (query params may be naive)
    range_start = start or datetime(2000, 1, 1)
    range_end = (end + timedelta(days=1)) if end else datetime(2100, 1, 1)
    if range_start.tzinfo is None:
        range_start = range_start.replace(tzinfo=timezone.utc)
    if range_end.tzinfo is None:
        range_end = range_end.replace(tzinfo=timezone.utc)

    for master in masters:
        try:
            duration = (master.end_time - master.start_time) if master.end_time else timedelta(hours=1)

            # Expand RRULE in the event's original timezone so DST is handled
            # correctly (e.g. "11 AM Eastern" stays 11 AM regardless of DST).
            orig_tz = None
            if master.original_timezone:
                try:
                    orig_tz = zoneinfo.ZoneInfo(master.original_timezone)
                except Exception:
                    pass

            if orig_tz:
                # Convert stored UTC start back to original local time for expansion
                dtstart_utc = master.start_time
                if dtstart_utc.tzinfo is None:
                    dtstart_utc = dtstart_utc.replace(tzinfo=timezone.utc)
                dtstart_local = dtstart_utc.astimezone(orig_tz)

                # Expand in local timezone
                local_range_start = range_start.astimezone(orig_tz)
                local_range_end = range_end.astimezone(orig_tz)
                rule = rrulestr(master.rrule, dtstart=dtstart_local)
                occurrences_local = rule.between(local_range_start, local_range_end, inc=True)

                # Convert each occurrence back to UTC
                occurrences = [occ.astimezone(timezone.utc) for occ in occurrences_local]
            else:
                dtstart = master.start_time
                if dtstart.tzinfo is None:
                    dtstart = dtstart.replace(tzinfo=timezone.utc)
                rule = rrulestr(master.rrule, dtstart=dtstart)
                occurrences = rule.between(range_start, range_end, inc=True)

            master_exceptions = exc_by_master.get(master.id, {})

            for occ_dt in occurrences:
                occ_iso = occ_dt.isoformat()
                # Check if an exception overrides this occurrence
                if occ_iso in master_exceptions:
                    exc_event = master_exceptions[occ_iso]
                    event_responses.append(await _build_event_response(exc_event, db))
                    continue

                # Generate virtual instance
                occ_end = occ_dt + duration
                synthetic_id = f"{master.id}__rec__{occ_dt.strftime('%Y%m%dT%H%M%S')}"
                # Ensure datetimes are UTC-aware
                synced = master.synced_at.replace(tzinfo=timezone.utc) if master.synced_at and master.synced_at.tzinfo is None else master.synced_at
                created = master.created_at.replace(tzinfo=timezone.utc) if master.created_at and master.created_at.tzinfo is None else master.created_at
                updated = master.updated_at.replace(tzinfo=timezone.utc) if master.updated_at and master.updated_at.tzinfo is None else master.updated_at
                event_responses.append(EventResponse(
                    id=synthetic_id,
                    title=master.title,
                    description=master.description or "",
                    start_time=occ_dt,
                    end_time=occ_end,
                    all_day=master.all_day,
                    location=master.location or "",
                    calendar_source=master.calendar_source or "local",
                    calendar_id=master.calendar_id or "",
                    rrule=master.rrule,
                    recurring_event_id=master.id,
                    recurrence_id=None,
                    synced_at=synced,
                    linked_notes=[],
                    linked_tasks=[],
                    created_at=created,
                    updated_at=updated,
                ))
        except Exception as e:
            logger.warning("Failed to expand RRULE for event %s: %s", master.id, e)
            event_responses.append(await _build_event_response(master, db))

    # Add any exception instances not already included (edge case: exception moved outside original date)
    included_exc_ids = set()
    for resp in event_responses:
        if resp.recurrence_id:
            included_exc_ids.add(resp.id)
    for exc in exceptions:
        if exc.id not in included_exc_ids:
            event_responses.append(await _build_event_response(exc, db))

    # Sort by start_time
    event_responses.sort(key=lambda e: e.start_time)
    total = len(event_responses)
    event_responses = event_responses[offset:offset + limit]
    return EventList(events=event_responses, total=total)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return await _build_event_response(event, db)


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(event_id: str, body: EventUpdate, db: AsyncSession = Depends(get_db), client_id: str | None = Depends(get_client_id)):
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        # Convert datetime fields to UTC
        if field in ("start_time", "end_time") and value is not None:
            value = _ensure_utc(value)
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    await manager.broadcast("event_updated", {"id": event.id, "title": event.title}, exclude_client_id=client_id)

    # Push update to CalDAV if event has a remote href and direction allows export (non-blocking)
    if event.caldav_href:
        try:
            settings_map = await _load_caldav_settings(db)
            direction = settings_map.get("calendar_sync_direction", "import")
            if direction in ("both", "export"):
                await caldav_sync_service.update_remote_event(event, settings_map)
        except Exception:
            logger.exception("CalDAV update failed for event (non-blocking)")

    return await _build_event_response(event, db)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str, db: AsyncSession = Depends(get_db), client_id: str | None = Depends(get_client_id)):
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    # Delete from CalDAV server first if it has a remote href and direction allows export (non-blocking)
    if event.caldav_href:
        try:
            settings_map = await _load_caldav_settings(db)
            direction = settings_map.get("calendar_sync_direction", "import")
            if direction in ("both", "export"):
                await caldav_sync_service.delete_remote_event(event, settings_map)
        except Exception:
            logger.exception("CalDAV delete failed for event (non-blocking)")

    await db.delete(event)
    await db.commit()
    await manager.broadcast("event_deleted", {"id": event_id}, exclude_client_id=client_id)


@router.delete("/events/{event_id}/series", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_series(event_id: str, db: AsyncSession = Depends(get_db), client_id: str | None = Depends(get_client_id)):
    """Delete a recurring master event and all its exception instances."""
    master = await db.get(CalendarEvent, event_id)
    if master is None:
        raise HTTPException(status_code=404, detail="Event not found")

    # Delete from CalDAV server if it has a remote href
    if master.caldav_href:
        try:
            settings_map = await _load_caldav_settings(db)
            await caldav_sync_service.delete_remote_event(master, settings_map)
        except Exception:
            logger.exception("CalDAV delete failed for series master (non-blocking)")

    # Delete all exception instances
    exc_result = await db.execute(
        select(CalendarEvent).where(CalendarEvent.recurring_event_id == event_id)
    )
    for exc in exc_result.scalars().all():
        await db.delete(exc)

    # Delete the master
    await db.delete(master)
    await db.commit()
    await manager.broadcast("event_series_deleted", {"id": event_id}, exclude_client_id=client_id)


@router.put("/events/{event_id}/recurrence", response_model=EventResponse)
async def update_event_recurrence(event_id: str, body: EventUpdate, db: AsyncSession = Depends(get_db), client_id: str | None = Depends(get_client_id)):
    """Update the RRULE on a master recurring event."""
    event = await db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if body.rrule is not None:
        event.rrule = body.rrule if body.rrule else None

    await db.commit()
    await db.refresh(event)

    # Push update to CalDAV if event has a remote href
    if event.caldav_href:
        try:
            settings_map = await _load_caldav_settings(db)
            await caldav_sync_service.update_remote_event(event, settings_map)
        except Exception:
            logger.exception("CalDAV update failed for recurrence change (non-blocking)")

    await manager.broadcast("event_updated", {"id": event.id, "title": event.title}, exclude_client_id=client_id)
    return await _build_event_response(event, db)


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
        sync_interval_minutes=int(settings_map.get("calendar_sync_interval_minutes", "0")),
        sync_direction=settings_map.get("calendar_sync_direction", "import"),
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
    if body.sync_interval_minutes is not None:
        updates["calendar_sync_interval_minutes"] = str(body.sync_interval_minutes)
    if body.sync_direction is not None:
        updates["calendar_sync_direction"] = body.sync_direction
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
