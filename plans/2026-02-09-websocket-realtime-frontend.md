# WebSocket Real-Time Frontend Updates

## Plan

Wire up frontend pages to automatically refresh when relevant WebSocket events arrive, and add missing broadcasts to MCP tools.

### Step 1: MCP Server Broadcasts
Add `await manager.broadcast(...)` after each mutation commit in `api/mcp/server.py` for 10 tools (create/update/delete for tasks, notes, calendar events, plus link_note_to_task).

### Step 2: WebSocket Store Subscriptions
Add `on(eventTypes, callback, debounceMs)` method to `ui/src/lib/stores/websocket.svelte.ts` with per-subscription debouncing, timer cleanup, and unsubscribe support.

### Step 3: Page Subscriptions
- Notes layout: refresh sidebar list on note CRUD + AI tags (500ms debounce)
- Note editor: reload if same note updated externally AND no unsaved changes (1000ms); navigate away on deletion (0ms)
- Tasks page: reload tasks + projects on task CRUD + project updates (500ms)
- Calendar: reload data on event/task CRUD (500ms)
- Dashboard: reload on all data events (2000ms debounce)

## Implementation Log

### Completed 2026-02-09

1. **`api/mcp/server.py`** — Imported `manager` from `api.utils.websocket`. Added broadcasts:
   - `_create_task` → `task_created`
   - `_update_task` → `task_updated`
   - `_delete_task` → `task_deleted`
   - `_create_note` → `note_created`
   - `_update_note` → `note_updated`
   - `_delete_note` → `note_deleted`
   - `_link_note_to_task` → `task_updated`
   - `_create_calendar_event` → `event_created`
   - `_update_calendar_event` → `event_updated`
   - `_delete_calendar_event` → `event_deleted`

2. **`ui/src/lib/stores/websocket.svelte.ts`** — Added `on()` method with:
   - `Map<string, Set<Sub>>` subscription registry
   - Per-subscription debounce timers
   - Last event data forwarding
   - Unsubscribe function that clears timers

3. **Page subscriptions added (all silent — no loading spinners, targeted updates):**
   - `ui/src/routes/notes/+layout.svelte` — split by event type:
     - `note_deleted`: filter from local array + refresh tags (0ms, no API call for list)
     - `note_updated`/`ai_tags_suggested`: fetch single note → patch in-place + refresh tags (500ms)
     - `note_created`: silent list re-fetch without loading spinner (500ms)
   - `ui/src/routes/notes/[id]/+page.svelte` — note reload with unsaved-changes guard (1000ms) + deletion redirect (0ms)
   - `ui/src/routes/tasks/[projectId]/+page.svelte` — silent tasks + projects re-fetch, updates `selectedTask` in-place (500ms)
   - `ui/src/routes/calendar/+page.svelte` — silent data re-fetch, preserves view/date/panel state (500ms)
   - `ui/src/routes/+page.svelte` — silent dashboard data re-fetch, skips AI suggestions (2000ms)

4. **Verification**: `svelte-check` passes with 0 errors.
