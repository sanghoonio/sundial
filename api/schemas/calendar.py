from datetime import datetime

from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    description: str = ""
    start_time: datetime
    end_time: datetime | None = None
    all_day: bool = False
    location: str = ""
    rrule: str | None = None
    original_timezone: str | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    all_day: bool | None = None
    location: str | None = None
    rrule: str | None = None


class LinkedNoteRef(BaseModel):
    id: str
    title: str


class LinkedTaskRef(BaseModel):
    id: str
    title: str
    status: str


class EventResponse(BaseModel):
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime | None
    all_day: bool
    location: str
    calendar_source: str
    calendar_id: str = ""
    rrule: str | None = None
    recurring_event_id: str | None = None
    recurrence_id: str | None = None
    synced_at: datetime | None = None
    linked_notes: list[LinkedNoteRef] = []
    linked_tasks: list[LinkedTaskRef] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventList(BaseModel):
    events: list[EventResponse]
    total: int


class CalendarSettingsResponse(BaseModel):
    calendar_source: str = ""
    sync_enabled: bool = False
    selected_calendars: list[str] = []
    sync_range_past_days: int = 30
    sync_range_future_days: int = 90
    sync_interval_minutes: int = 0
    sync_direction: str = "import"  # "import", "export", "both"
    caldav_server_url: str = ""
    caldav_username: str = ""
    caldav_has_password: bool = False
    last_sync_at: str | None = None
    last_sync_error: str | None = None


class CalendarSettingsUpdate(BaseModel):
    calendar_source: str | None = None
    sync_enabled: bool | None = None
    selected_calendars: list[str] | None = None
    sync_range_past_days: int | None = None
    sync_range_future_days: int | None = None
    sync_interval_minutes: int | None = None
    sync_direction: str | None = None
    caldav_server_url: str | None = None
    caldav_username: str | None = None
    caldav_password: str | None = None


class CalendarSyncResult(BaseModel):
    synced_events: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    errors: list[str] = []
    last_sync: str | None = None


class CalDAVCalendarInfo(BaseModel):
    id: str
    name: str
    color: str = ""
