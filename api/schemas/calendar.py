from datetime import datetime

from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    description: str = ""
    start_time: datetime
    end_time: datetime | None = None
    all_day: bool = False
    location: str = ""


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    all_day: bool | None = None
    location: str | None = None


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
    synced_at: datetime | None = None
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


class CalendarSettingsUpdate(BaseModel):
    calendar_source: str | None = None
    sync_enabled: bool | None = None
    selected_calendars: list[str] | None = None
    sync_range_past_days: int | None = None
    sync_range_future_days: int | None = None
