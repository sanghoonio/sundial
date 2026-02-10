# Eliminate Duplicate Refresh: Server-Side Client Exclusion

## Context

After adding WebSocket-driven frontend refreshes, every local mutation both updates UI optimistically AND triggers a WS broadcast that bounces back to the same client, causing a redundant re-fetch. The note editor worked around this with a brittle 2-second cooldown hack. This plan adds a `client_id` mechanism so the server never sends a broadcast back to the client that initiated the mutation.

## Implementation Log

### Files Created
- `ui/src/lib/clientId.ts` — shared UUID generated once per page load

### Files Modified

**Frontend:**
- `ui/src/lib/services/websocket.ts` — appends `?client_id=xxx` to WS URL
- `ui/src/lib/services/api.ts` — sends `X-Client-ID: xxx` header on every request
- `ui/src/routes/notes/[id]/+page.svelte` — removed `lastSaveTime` variable and 2-second cooldown hack

**Backend:**
- `api/utils/websocket.py` — `active_connections` stores `(WebSocket, client_id)` tuples; `broadcast()` accepts `exclude_client_id`; added `get_client_id()` FastAPI dependency
- `api/main.py` — WS endpoint extracts `client_id` from query params
- `api/routes/tasks.py` — all 6 mutating handlers now accept `client_id` dependency and pass `exclude_client_id` (7 broadcast calls)
- `api/routes/notes.py` — `create_note`, `update_note`, `delete_note` (3 broadcast calls)
- `api/routes/calendar.py` — `create_event`, `update_event`, `delete_event`, `delete_event_series`, `update_event_recurrence` (5 broadcast calls)
- `api/routes/projects.py` — `update_project` (1 broadcast call)

**Untouched (by design):**
- `api/mcp/server.py` — MCP broadcasts reach all clients
- `api/services/ai_background.py` — AI background broadcasts reach all clients
