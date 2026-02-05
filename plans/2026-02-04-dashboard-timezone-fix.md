# Fix: Dashboard shows tomorrow's tasks today (UTC timezone bug)

## Problem

The dashboard calculates "today" in UTC. For a user in e.g. UTC-8, after 4PM local time (midnight UTC), the dashboard's "today" rolls over to the next calendar day.

## Implementation Log

### Changes Made

1. **`api/utils/timezone.py`** (new) - `resolve_today(tz)` helper that calculates midnight-to-midnight in the user's IANA timezone, converts to UTC for DB queries, and returns the local date string. Falls back to UTC behavior when `tz` is None.

2. **`api/routes/dashboard.py`** - Added `tz: str | None = Query(None)` param to both `get_today()` and `get_journal_data()`. Replaced inline UTC date math with `resolve_today(tz)`. Response `date` field now uses `local_date`.

3. **`api/routes/ai.py`** - Added `tz: str | None = Query(None)` param to `daily_suggestions()`. Replaced inline UTC date math with `resolve_today(tz)`.

4. **`api/mcp/server.py`** - Added `tz` property to `get_dashboard` tool schema. Inline timezone logic in `_get_dashboard()` (can't use FastAPI's HTTPException here, returns TextContent error instead). Dashboard header uses `local_date`.

5. **`ui/src/routes/+page.svelte`** - Sends `?tz=<IANA>` with both `/api/dashboard/today` and `/api/ai/suggestions/daily` fetches using `Intl.DateTimeFormat().resolvedOptions().timeZone`.

6. **`ui/src/routes/notes/+layout.svelte`** - Sends `?tz=<IANA>` with `/api/dashboard/journal-data` fetch.

### Backward Compatibility

All `tz` parameters are optional and default to `None`, preserving the existing UTC behavior for any callers that don't send it (e.g., older MCP clients).
