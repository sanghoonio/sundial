# Database Model Redundancy Cleanup - source_note_id Removal

## Summary

Removed the redundant `source_note_id` field from the Task model. All task-note links now use the `TaskNote` junction table exclusively.

---

## Implementation Log

### Phase 1: Backend Changes

#### 1.1 Model Changes
**File:** `api/models/task.py`
- Removed `source_note_id` column from Task model
- Removed `source_note` relationship

#### 1.2 Service Changes
**File:** `api/services/task_service.py`
- Removed `source_note_id` parameter from `create_task()`
- Removed `task.source_note_id = None` clearing logic from `update_task()`

**File:** `api/services/ai_background.py`
- Updated task existence check to use TaskNote join instead of `Task.source_note_id`
- Changed AI-suggested task creation to use `TaskNote` link instead of `source_note_id`

**File:** `api/services/note_service.py`
- Updated linked tasks query to use `TaskNote.task_id` instead of `Task.source_note_id`

#### 1.3 Schema Changes
**File:** `api/schemas/task.py`
- Removed `source_note_id` from `TaskCreate`
- Removed `source_note_id` from `TaskResponse`

#### 1.4 Route Changes
**File:** `api/routes/tasks.py`
- Removed `source_note_id` from `create_task()` service call
- Removed `source_note_id` from `_task_to_response()`

**File:** `api/routes/notes.py`
- Simplified `get_backlinks()` to only query `TaskNote` table
- Simplified `get_links()` incoming task links to only query `TaskNote` table
- Updated `_note_to_response()` to use `TaskNote.task_id`
- Updated `_note_to_list_item()` to use `TaskNote.task_id`

#### 1.5 MCP Changes
**File:** `api/mcp/server.py`
- Simplified `_get_note_links()` to only query `TaskNote` table

### Phase 2: Frontend Changes

#### 2.1 TypeScript Type Changes
**File:** `ui/src/lib/types.ts`
- Removed `source_note_id` from `TaskCreate`
- Removed `source_note_id` from `TaskResponse`

#### 2.2 Component Changes

**File:** `ui/src/lib/components/tasks/TaskDetailModal.svelte`
- Changed from fetching single `linkedNoteTitle` to `linkedNoteTitles` (Record)
- Updated linked items display to iterate over `task.note_ids`

**File:** `ui/src/lib/components/tasks/TaskDetailPanel.svelte`
- Removed merge logic that combined `source_note_id` into `noteIds`
- Now directly uses `task.note_ids`

**File:** `ui/src/lib/components/tasks/TaskCard.svelte`
- Changed `hasLinkedNote` to only check `note_ids.length > 0`

**File:** `ui/src/lib/components/tasks/TaskCreatePanel.svelte`
- Renamed prop from `sourceNoteId` to `initialNoteId`
- Changed to use `note_ids: [initialNoteId]` array instead of `source_note_id`

**File:** `ui/src/lib/components/tasks/TaskCreateModal.svelte`
- Renamed prop from `sourceNoteId` to `initialNoteId`
- Changed to use `note_ids: [initialNoteId]` array instead of `source_note_id`

**File:** `ui/src/routes/notes/[id]/+page.svelte`
- Updated `TaskCreatePanel` usage to use `initialNoteId` prop

---

## Database Migration Note

The existing migration in `api/init_db.py` already handles copying `source_note_id` values to the `task_notes` table. After deploying this change, the old `source_note_id` column will remain in the database but will be unused. It can be dropped in a future migration.

---

## Testing Checklist

- [x] Create task from note page → verify creates `TaskNote` entry
- [ ] Open task in TaskDetailModal → verify shows linked notes from `note_ids`
- [ ] Link/unlink notes in TaskDetailPanel → verify persists
- [ ] Check TaskCard shows note icon when `note_ids` populated
- [ ] Check note's backlinks/links shows linked tasks
- [ ] Test AI task extraction creates TaskNote links
- [ ] Test MCP get_note_links returns linked tasks
- [ ] Test MCP get_task_links returns linked notes

---

## Files Modified

### Backend (7 files)
- `api/models/task.py`
- `api/services/task_service.py`
- `api/services/ai_background.py`
- `api/services/note_service.py`
- `api/schemas/task.py`
- `api/routes/tasks.py`
- `api/routes/notes.py`
- `api/mcp/server.py`

### Frontend (7 files)
- `ui/src/lib/types.ts`
- `ui/src/lib/components/tasks/TaskDetailModal.svelte`
- `ui/src/lib/components/tasks/TaskDetailPanel.svelte`
- `ui/src/lib/components/tasks/TaskCard.svelte`
- `ui/src/lib/components/tasks/TaskCreatePanel.svelte`
- `ui/src/lib/components/tasks/TaskCreateModal.svelte`
- `ui/src/routes/notes/[id]/+page.svelte`
