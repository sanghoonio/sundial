# Implementation Log: Feature Batch (API Alignment, Notes UX, Import/Export, Toast Removal)

## Completed Features

### Feature 7: Remove All Toast Notifications
- Removed `toasts.svelte.ts` store and `Toast.svelte` component
- Removed toast imports and calls from 17+ files
- Replaced `toasts.error()` with `console.error()` in catch blocks
- Removed `<Toast />` from root `+layout.svelte`

### Feature 1A: Notes API — New Query Params
- Added `search` (FTS5), `tags` (comma-separated multi-tag AND filter), `date_from`, `date_to` to `GET /api/notes`
- Added `limit`/`offset` to `NoteList` response schema
- Updated `note_service.list_notes()` with all new filters

### Feature 1B: Tasks API — ai_suggested Filter
- Added `ai_suggested: bool | None` query param to `list_tasks` endpoint
- Added filter to `task_service.list_tasks()`

### Feature 1C: Calendar Events — Linked Notes/Tasks
- Added `LinkedNoteRef`, `LinkedTaskRef` schemas
- Added `linked_notes`, `linked_tasks` to `EventResponse`
- Created `_build_event_response()` helper in calendar routes

### Feature 1D: Search API — Task Search
- Added `TaskSearchResultItem` schema
- Added `type` query param (`notes`, `tasks`, `all`)
- Task search uses LIKE on title/description

### Feature 1E: Frontend API Wiring
- Notes layout uses server-side FTS5 search via `search` API param
- Search page displays task results alongside note results
- Added `TaskSearchResultItem` to frontend types

### Feature 2: New Note Autosave
- Replaced manual "Create" button with save status indicator (Save/Check icons)
- Added debounced auto-create ($effect watching title + blocks, 1s debounce)
- `creating` flag guards against double-creation
- Ctrl+S triggers immediate creation
- On create, navigates to `/notes/{id}` (edit page handles subsequent autosave)

### Feature 8: Double-Click Preview Toggle
- Added `ondblclicktoggle` prop to `NoteEditor` and `MarkdownBlock`
- `MarkdownBlock` fires on both preview div and edit container div
- Text selection guard: if text is selected, double-click doesn't toggle
- Both `[id]/+page.svelte` and `new/+page.svelte` pass the handler

### Feature 3: Note Import from Text/Markdown
- Created `NoteImportButton.svelte` component
- Supports `.md`, `.markdown`, `.txt` files
- Parses YAML frontmatter for title and tags (array and list formats)
- Falls back to filename for title
- Added import button to notes sidebar header

### Feature 4: Note Export (Download)
- Added download button (Download icon) to note edit top bar
- Generates markdown with YAML frontmatter (title, tags, created, updated)
- Uses Blob + createObjectURL pattern for browser download
- Filename: slugified title + `.md`

### Feature 5: Workspace Export as ZIP
- Created `api/routes/workspace.py` with `GET /api/export/workspace`
- Exports all 11 DB tables as `data.json` + note files in `notes/` directory
- Streams ZIP response with `StreamingResponse`
- Registered router in `api/main.py`

### Feature 6: Workspace Restore from ZIP
- Added `POST /api/import/workspace` in same route file
- Validates ZIP structure (requires `data.json`)
- Clears existing data in dependency order
- Restores records from JSON, files from ZIP
- Rebuilds FTS5 index after restore
- Settings page UI: Data card with export/import buttons and confirmation dialog

## Files Modified/Created

### Backend
- `api/routes/notes.py` — new query params
- `api/services/note_service.py` — new filters
- `api/schemas/note.py` — NoteList limit/offset
- `api/routes/tasks.py` — ai_suggested param
- `api/services/task_service.py` — ai_suggested filter
- `api/routes/calendar.py` — linked items helper
- `api/schemas/calendar.py` — LinkedNoteRef, LinkedTaskRef, EventResponse update
- `api/routes/search.py` — type param, task search
- `api/schemas/search.py` — TaskSearchResultItem
- `api/routes/workspace.py` — NEW (export/import endpoints)
- `api/main.py` — registered workspace router

### Frontend
- `ui/src/lib/services/api.ts` — added `authHeaders()` method
- `ui/src/lib/types.ts` — TaskSearchResultItem, SearchResult tasks field
- `ui/src/lib/components/notes/NoteEditor.svelte` — ondblclicktoggle prop
- `ui/src/lib/components/notes/MarkdownBlock.svelte` — ondblclicktoggle prop + handler
- `ui/src/lib/components/notes/NoteImportButton.svelte` — NEW
- `ui/src/routes/notes/+layout.svelte` — server-side search, import button
- `ui/src/routes/notes/new/+page.svelte` — autosave, save status indicator
- `ui/src/routes/notes/[id]/+page.svelte` — download button, dblclick toggle
- `ui/src/routes/search/+page.svelte` — task results display
- `ui/src/routes/settings/+page.svelte` — Data card (export/import)
- 17+ files: toast removal

### Deleted
- `ui/src/lib/stores/toasts.svelte.ts`
- `ui/src/lib/components/ui/Toast.svelte`

## Verification
- Frontend build: passes (`npm run build`)
- Backend imports: verified (`from api.routes.workspace import router`)
- Routes registered: `/api/export/workspace`, `/api/import/workspace` confirmed
