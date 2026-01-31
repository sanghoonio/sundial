from pydantic import BaseModel


class SettingsResponse(BaseModel):
    ai_enabled: bool = False
    ai_auto_tag: bool = False
    ai_auto_extract_tasks: bool = False
    calendar_source: str = ""
    calendar_sync_enabled: bool = False
    theme: str = "light"


class SettingsUpdate(BaseModel):
    ai_enabled: bool | None = None
    ai_auto_tag: bool | None = None
    ai_auto_extract_tasks: bool | None = None
    calendar_source: str | None = None
    calendar_sync_enabled: bool | None = None
    theme: str | None = None
