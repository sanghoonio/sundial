# Simplify Task Status: Two-State Checkmark Toggle

## Implementation Log

### Backend (api/)
- **`models/task.py:20`** — Changed default status from `"open"` to `"in_progress"`
- **`init_db.py`** — Added idempotent migration: `UPDATE tasks SET status = 'in_progress' WHERE status = 'open'`; changed inbox seed milestones from 3 to 2 (removed "Done")
- **`routes/projects.py:33`** — Changed default milestones for new projects from `["To Do", "In Progress", "Done"]` to `["To Do", "In Progress"]`
- **`routes/tasks.py`** — Fixed partial update bug: used `model_fields_set` to distinguish "not provided" from "explicitly null", preventing milestone/due_date clearing on status-only updates
- **`mcp/server.py`** — Updated status enums in `list_tasks` and `update_task` from `["open", "in_progress", "done"]` to `["in_progress", "done"]`

### TaskCard (`TaskCard.svelte`)
- Added `onstatustoggle` prop
- Added checkmark circle button (hollow/filled) before title
- Done tasks get `line-through text-base-content/40` on title
- Fixed overdue derived: only shows overdue when `status !== 'done'`

### KanbanBoard/Column
- **KanbanBoard**: Done tasks are excluded from regular milestone columns. A virtual "Done" column appears at the end (before "Add column") showing all completed tasks sorted by completion time, with count badge and `CircleCheckBig` icon. Tasks in the Done column render at `opacity-50`.
- **KanbanColumn**: Added `onstatustoggle` prop; passes to TaskCard; wraps done task cards in `opacity-50`

### Tasks Page (`[projectId]/+page.svelte`)
- Added `handleStatusToggle()` with optimistic update + API call
- Passes `onstatustoggle` to KanbanBoard

### Detail Panels
- **TaskDetailPanel**: Replaced status `<select>` with checkbox + label ("Completed" / "In progress"); changed default from `'open'` to `'in_progress'`
- **TaskDetailModal**: Same replacement

### Status Badges
- **Notes page**: Simplified 3-state badge to 2-state (`badge-success` for done, `badge-ghost` otherwise)
- **EventPanel**: Same simplification
- **Search page**: Same simplification with updated label text

### Bug fix: Partial update clearing milestone_id
The `TaskUpdate` Pydantic schema defaults all fields to `None`. When a partial update like `{ status: "done" }` was sent, `milestone_id` would be `None` in the parsed body, and the service would interpret that as "clear the milestone." Fixed by checking `body.model_fields_set` in the route to only pass fields that were actually present in the request JSON, using the `_UNSET` sentinel for unprovided nullable fields.
