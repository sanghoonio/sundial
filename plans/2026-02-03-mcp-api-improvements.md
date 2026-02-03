# MCP API Improvements

## Summary

Implemented priority fixes and feature additions for the MCP API based on the evaluation plan.

## Changes Made

### 1. Bug Fix: Status Value Mismatch

**File:** `api/mcp/server.py`

Fixed the status descriptions in `list_tasks` and `update_task` tools:
- Changed from incorrect `todo/in_progress/done` to correct `open/in_progress/done`
- Added `enum` constraint to ensure LLMs use valid values

### 2. New Tool: `list_projects`

Enables discovery of valid project IDs. Returns:
- Project ID, name, status
- Task count per project
- Description (truncated if long)

### 3. New Tool: `list_tags`

Enables discovery of valid tag names. Returns:
- Tag name
- Note count (usage frequency)

### 4. New Tool: `create_note`

Enables note creation via MCP. Parameters:
- `title` (required): Note title
- `content`: Markdown content
- `tags`: Array of tag names to apply
- `project_id`: Project to associate with

Uses existing `note_service.create_note()` to ensure:
- Proper filepath generation
- FTS index updates
- Wiki-link parsing
- Tag sync

### 5. New Tool: `update_note`

Enables note modification via MCP. Parameters:
- `note_id` (required): Note ID to update
- `title`: New title
- `content`: New content
- `tags`: Replace all tags

Uses existing `note_service.update_note()` for consistency.

## Tool Count

MCP API now exposes 12 tools (up from 8):
1. `search_notes`
2. `get_note`
3. `list_notes`
4. `list_tasks`
5. `create_task`
6. `update_task`
7. `get_calendar_events`
8. `get_dashboard`
9. `list_projects` (new)
10. `list_tags` (new)
11. `create_note` (new)
12. `update_note` (new)

## Verification

```bash
source .venv/bin/activate && python -c "from api.mcp.server import _tool_list; tools = _tool_list(); print(f'Loaded {len(tools)} tools')"
# Output: Loaded 12 tools
```

## Testing

To test the new tools:
1. Start API: `uv run uvicorn api.main:app --reload`
2. Connect MCP client to `http://localhost:8000/mcp/sse`
3. Test each tool:
   - `list_projects` → returns project list with task counts
   - `list_tags` → returns tag list with note counts
   - `list_tasks` with `status: "open"` → works correctly (not "todo")
   - `create_note` with title + content → returns new note ID
   - `get_note` with that ID → confirms content
   - `update_note` to change title → confirms update

---

## Follow-up: MCP Settings UI

### Added Features

1. **`mcp_enabled` Setting**
   - New setting to enable/disable MCP server
   - Default: `true` (enabled)
   - When disabled, MCP endpoints return 403 Forbidden

2. **AI Settings Page MCP Section**
   - Toggle to enable/disable MCP
   - Dynamic URL generation using `window.location.origin`
   - Copy-to-clipboard for Claude Desktop config JSON
   - Step-by-step setup instructions
   - Links to the Tokens settings page

### Files Modified

| File | Changes |
|------|---------|
| `api/routes/settings.py` | Added `mcp_enabled` to settings keys |
| `api/schemas/settings.py` | Added `mcp_enabled` to response/update schemas |
| `api/mcp/routes.py` | Added `_check_mcp_enabled()` function, returns 403 if disabled |
| `ui/src/lib/types.ts` | Added `mcp_enabled` to TypeScript interfaces |
| `ui/src/routes/settings/ai/+page.svelte` | Added MCP section with toggle, config, and instructions |

### UI Features

- MCP toggle is always visible (independent of AI enabled state)
- Config JSON uses dynamic URL based on current origin (works for localhost and remote deployments)
- Copy button with visual feedback
- Clear setup instructions with config file paths for macOS and Windows
- Link to Tokens page for creating API keys
