# Hybrid AI Features: OpenRouter (Push) + MCP Server (Pull)

## Plan

Two-part AI integration for Sundial:
1. **OpenRouter API** — Powers all in-app AI: auto-tagging, task extraction, event linking, daily suggestions, chat blocks
2. **MCP Server** — Sundial exposes itself as an MCP server for Claude Desktop / other MCP clients to query notes, tasks, calendar

## Implementation Log

### Step 1: Settings Infrastructure
- Added `openrouter_api_key` and `openrouter_model` fields to `SettingsResponse` and `SettingsUpdate` schemas
- Added keys to `_SETTINGS_KEYS` in settings route with masking support
- Masked API key in GET responses (shows `****` + last 4 chars)
- PUT skips overwriting if masked value sent back unchanged
- Removed unused `ANTHROPIC_API_KEY` from `api/config.py`
- Updated `ui/src/lib/types.ts` with new settings fields
- Expanded `ui/src/routes/settings/ai/+page.svelte` with:
  - Password input for API key (only sends on change)
  - Model ID text input with helper links
  - Status indicator (configured/not set)

### Step 2: AI Service Core + Prompts
- Added `httpx>=0.27.0` and `mcp>=1.0.0` to `api/requirements.txt`
- Created `api/services/ai_prompts.py` with system prompts for:
  - SYSTEM_CHAT, SYSTEM_AUTO_TAG, SYSTEM_EXTRACT_TASKS, SYSTEM_LINK_EVENTS, SYSTEM_DAILY_SUGGESTIONS
- Rewrote `api/services/ai_service.py` with:
  - `_get_config(db)` reads settings from user_settings table
  - `_call_openrouter()` httpx POST to OpenRouter API
  - `_parse_json_response()` strips markdown code block wrappers
  - `chat()`, `auto_tag()`, `extract_tasks()`, `link_events()`, `daily_suggestions()`
  - Content truncation to 8000 chars
  - Error handling for 401/429 and generic failures

### Step 3: Chat & Suggestions Endpoints
- Rewrote `api/routes/ai.py`:
  - `POST /api/ai/chat` — builds context from note, calls OpenRouter
  - `POST /api/ai/analyze-note/{note_id}` — queues background AI processing
  - `GET /api/ai/suggestions/daily` — gathers events/tasks/notes, returns AI summary
- New response models: `ChatResponse` (response + error fields), `DailySuggestionsResponse`

### Step 4: Background AI Processing
- Created `api/services/ai_background.py`:
  - `process_note_ai()` — entry point from BackgroundTasks
  - Checks ai_enabled, api_key, debounces (30s)
  - `_run_auto_tag()` — AI suggests tags, adds with ai_suggested=True
  - `_run_extract_tasks()` — AI extracts tasks, creates with source_note_id
  - `_run_link_events()` — AI matches to recent calendar events
  - Each operation creates AIProcessingQueue entry, broadcasts WebSocket event
- Wired into `api/routes/notes.py`:
  - `create_note` and `update_note` now trigger `process_note_ai` via BackgroundTasks

### Step 5: Frontend AI Feedback
- Updated `ChatBlock.svelte` to match new API response format
- Updated `websocket.svelte.ts` to handle AI events:
  - `ai_tags_suggested` → toast showing suggested tags
  - `ai_tasks_extracted` → toast with count of extracted tasks
  - `ai_events_linked` → toast with count of linked events

### Step 6: MCP Server
- Created `api/mcp/__init__.py`
- Created `api/mcp/server.py` with 8 tools:
  - `search_notes`, `get_note`, `list_notes`
  - `list_tasks`, `create_task`, `update_task`
  - `get_calendar_events`, `get_dashboard`
- Created `api/mcp/routes.py`:
  - SSE transport via `SseServerTransport`
  - Starlette sub-app mounted at `/mcp`
  - Bearer token auth inline (validates against AuthToken table)
- Mounted in `api/main.py` via `app.mount("/mcp", mcp_app)`

### Files Modified
- `api/config.py` — removed ANTHROPIC_API_KEY
- `api/requirements.txt` — added httpx, mcp
- `api/schemas/settings.py` — added openrouter fields
- `api/routes/settings.py` — added keys, masking, skip-masked logic
- `api/services/ai_service.py` — full rewrite for OpenRouter
- `api/routes/ai.py` — rewritten endpoints
- `api/routes/notes.py` — added BackgroundTasks triggers
- `api/main.py` — mounted MCP app
- `ui/src/lib/types.ts` — added settings fields
- `ui/src/routes/settings/ai/+page.svelte` — expanded with API key/model UI
- `ui/src/lib/components/notes/ChatBlock.svelte` — updated API response handling
- `ui/src/lib/stores/websocket.svelte.ts` — added AI event toast handlers

### Files Created
- `api/services/ai_prompts.py`
- `api/services/ai_background.py`
- `api/mcp/__init__.py`
- `api/mcp/server.py`
- `api/mcp/routes.py`
