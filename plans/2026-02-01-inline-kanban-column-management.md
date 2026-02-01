# Inline Kanban Column Management

## Summary

Replace the modal-based milestone management with direct inline interactions on the kanban board itself. Users can rename, delete, reorder, and add columns without opening a settings modal.

## Changes

### 1. KanbanColumn header — inline rename + delete + column drag

**File:** `ui/src/lib/components/tasks/KanbanColumn.svelte`

- Replaced `<h3>` with a click-to-edit inline input (transparent bg, `focus:bg-base-300`, no border)
- Replaced task count badge with a trash button (ghost, small, hover text-error, confirm before delete)
- On rename blur/Enter: calls `onrename?.(milestone.id, newName)` callback
- On delete: calls `ondelete?.(milestone.id)` callback
- Made header area draggable for column reorder with `data-column-drag` attribute
- Uses `application/column-id` MIME type to distinguish from task drags (`text/plain`)
- Removed `onfullcreate` prop

### 2. KanbanBoard — column reorder + "Add column" placeholder

**File:** `ui/src/lib/components/tasks/KanbanBoard.svelte`

- Added `oncolumnrename`, `oncolumndelete`, `oncolumncreate`, `oncolumnreorder` props
- Passes `onrename` and `ondelete` down to each KanbanColumn
- Board-level drop handling detects `application/column-id` drags and calculates insertion position
- Shows a blue vertical drop indicator between columns during column drag
- After the last column, renders an "Add column" placeholder (border-dashed, bg-base-200/30)
- Click reveals inline text input with confirm/cancel buttons
- Removed `onfullcreate` prop

### 3. TaskQuickAdd — removed expand buttons

**File:** `ui/src/lib/components/tasks/TaskQuickAdd.svelte`

- Removed `Expand` icon import and both expand buttons
- Removed `onfullcreate` prop entirely

### 4. Project detail page — column operations wired up

**File:** `ui/src/routes/projects/[id]/+page.svelte`

- Added handler functions: `handleColumnRename`, `handleColumnDelete`, `handleColumnCreate`, `handleColumnReorder`
- Shared `saveMilestones()` helper that PUTs to `/api/projects/{id}/milestones`
- Passed column callbacks to KanbanBoard
- Removed from settings modal: entire "Milestones (columns)" section
- Removed unused state: `editMilestones`, `newMilestoneName`
- Removed unused functions: `addMilestone()`, `removeMilestone()`, `moveMilestone()`
- Removed unused imports: `ChevronUp`, `ChevronDown`, `Plus`

### 5. Tasks page — column operations wired up

**File:** `ui/src/routes/tasks/+page.svelte`

- Same column operation handlers as project page, operating on the selected project's milestones
- `saveMilestones()` updates the `projects` array in place after API response
- Removed `openFullCreate` function and `onfullcreate` prop from KanbanBoard

## Implementation Log

- All 5 files modified
- `svelte-check`: 0 errors, 8 warnings (all pre-existing)
- `vite build`: success
