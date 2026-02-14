from pydantic import BaseModel


class SettingsResponse(BaseModel):
    ai_enabled: bool = False
    ai_auto_tag: bool = False
    ai_auto_extract_tasks: bool = False
    ai_auto_link_events: bool = False
    ai_daily_suggestions: bool = True
    ai_provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4"
    nvidia_api_key: str = ""
    nvidia_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    calendar_source: str = ""
    calendar_sync_enabled: bool = False
    theme: str = "light"
    sidebar_default_collapsed: bool = False
    mcp_enabled: bool = True
    editor_toolbar_style: str = "float"


class SettingsUpdate(BaseModel):
    ai_enabled: bool | None = None
    ai_auto_tag: bool | None = None
    ai_auto_extract_tasks: bool | None = None
    ai_auto_link_events: bool | None = None
    ai_daily_suggestions: bool | None = None
    ai_provider: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    nvidia_api_key: str | None = None
    nvidia_model: str | None = None
    calendar_source: str | None = None
    calendar_sync_enabled: bool | None = None
    theme: str | None = None
    sidebar_default_collapsed: bool | None = None
    mcp_enabled: bool | None = None
    editor_toolbar_style: str | None = None
