# Recurring Tasks

## Context

Tasks in Sundial are currently one-off items. This plan adds recurring tasks using a **spawn-on-complete** model: when a recurring task is completed, the backend automatically creates the next instance with an advanced due date. This avoids cluttering the kanban board with future instances (unlike calendar's master-instance approach) and keeps each instance as an independent, editable task.

**Key behaviors:**
- **Complete** a recurring task → next instance spawns with the next due date
- **Delete** a recurring task → series stops (no spawn, since there's only one active instance at a time)
- **Edit recurrence** on any instance → affects future spawns only

## Database Changes

**File: `api/models/task.py`** - Add two columns to Task:
- `recurrence_rule` (Text, nullable) - RRULE string (e.g., `FREQ=WEEKLY`)
- `recurring_series_id` (String, nullable) - groups tasks in same series (format: `rseries_{hex}`)

**File: `api/init_db.py`** - ALTER TABLE migration for both columns

## Backend Changes

### New file: `api/utils/recurrence.py`
Utility functions:
- `generate_series_id()` → `rseries_{12-char hex}`
- `next_occurrence(rrule_str, after_dt)` → next datetime using `dateutil.rrule` (already a dependency)
- `human_readable_rule(rrule_str)` → display string like "Every week"

### File: `api/schemas/task.py`
- Add `recurrence_rule: str | None = None` to `TaskCreate` and `TaskUpdate`
- Add `recurrence_rule: str | None` and `recurring_series_id: str | None` to `TaskResponse`

### File: `api/services/task_service.py`
- `create_task()`: accept `recurrence_rule` param; generate `recurring_series_id` if rule is set
- `update_task()`: accept `recurrence_rule` param; on status→done with a recurrence rule + due_date, call `_spawn_recurring_task()`
- New `_spawn_recurring_task(db, source_task, next_due)`: creates next instance copying title, description, priority, project, milestone, recurrence_rule, series_id; copies checklist items (all unchecked); returns the spawned task
- `update_task()` returns a tuple `(task, spawned_task | None)` so the route can broadcast both events

### File: `api/routes/tasks.py`
- `create_task`: pass `recurrence_rule` to service
- `update_task`: pass `recurrence_rule` to service; handle tuple return; broadcast `task_created` for spawned task
- `_task_to_response`: include `recurrence_rule` and `recurring_series_id`

### File: `api/mcp/server.py`
- `create_task` / `update_task` tools: accept `recurrence_rule` param (simple presets like "daily"/"weekly" auto-converted to RRULE)
- `list_tasks` output: show recurrence info

## Frontend Changes

### File: `ui/src/lib/types.ts`
- Add `recurrence_rule?: string | null` to `TaskCreate`, `TaskUpdate`
- Add `recurrence_rule: string | null` and `recurring_series_id: string | null` to `TaskResponse`

### Reuse existing: `ui/src/lib/components/calendar/RecurrenceInput.svelte`
This component already handles FREQ selection (Daily/Weekly/Monthly/Yearly), end conditions (never/count/until), and builds RRULE strings. Reuse it directly in task panels/modals.

### File: `ui/src/lib/components/tasks/TaskCard.svelte`
- Import `Repeat` from lucide (already used in RecurrenceInput)
- Show small Repeat icon on cards that have `recurrence_rule` set

### File: `ui/src/lib/components/tasks/TaskDetailPanel.svelte`
- Add RecurrenceInput below the due date field
- Track `recurrenceRule` in component state
- Include in snapshot for auto-save
- Pass to API on save

### File: `ui/src/lib/components/tasks/TaskCreatePanel.svelte`
- Same as TaskDetailPanel: add RecurrenceInput and include in creation payload

### File: `ui/src/lib/components/tasks/TaskCreateModal.svelte`
- Same: add RecurrenceInput and include in creation payload

## Implementation Order

1. DB schema + model changes (`task.py`, `init_db.py`)
2. Recurrence utils (`api/utils/recurrence.py`)
3. Pydantic schemas (`schemas/task.py`)
4. Service layer spawn logic (`task_service.py`)
5. API routes (`routes/tasks.py`)
6. MCP tools (`mcp/server.py`)
7. Frontend types (`types.ts`)
8. TaskCard repeat icon
9. TaskDetailPanel / TaskCreatePanel / TaskCreateModal recurrence input

## Implementation Log

- [x] DB schema + model (`api/models/task.py`, `api/init_db.py`)
- [x] Recurrence utils (`api/utils/recurrence.py`)
- [x] Pydantic schemas (`api/schemas/task.py`)
- [x] Service layer (`api/services/task_service.py`) - spawn-on-complete + tuple return
- [x] API routes (`api/routes/tasks.py`) - pass recurrence_rule, broadcast spawned task
- [x] MCP tools (`api/mcp/server.py`) - preset normalization, spawn-on-complete
- [x] Frontend types + components (types.ts, TaskCard, TaskDetailPanel, TaskCreatePanel, TaskCreateModal)
- [x] All Python imports verified, recurrence utils tested, svelte-check 0 errors
