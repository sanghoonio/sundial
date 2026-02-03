from pydantic import BaseModel


class SettingsResponse(BaseModel):
    ai_enabled: bool = False
    ai_auto_tag: bool = False
    ai_auto_extract_tasks: bool = False
    ai_auto_link_events: bool = False
    ai_daily_suggestions: bool = True
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4"
    calendar_source: str = ""
    calendar_sync_enabled: bool = False
    theme: str = "light"


class SettingsUpdate(BaseModel):
    ai_enabled: bool | None = None
    ai_auto_tag: bool | None = None
    ai_auto_extract_tasks: bool | None = None
    ai_auto_link_events: bool | None = None
    ai_daily_suggestions: bool | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    calendar_source: str | None = None
    calendar_sync_enabled: bool | None = None
    theme: str | None = None
