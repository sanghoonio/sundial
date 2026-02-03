# Plan: Tasks Page Routing + Drag-and-Drop Placeholder Boxes

## Issue 1: URL-based project routing on tasks page

**Problem:** Switching projects only updates local state — the URL stays at `/tasks`. Browser back/forward buttons don't work, and there's no way to deep-link to a specific project.

**Solution:** Sync `selectedProjectId` with the `?project=` query parameter using SvelteKit's `goto()`.

### Changes in `ui/src/routes/tasks/+page.svelte`

1. Import `goto` from `$app/navigation`
2. When user clicks a project in the dropdown, call `goto` to update the URL query param instead of just setting state
3. Make `selectedProjectId` reactive to URL changes so browser back/forward works — derive it from `page.url.searchParams` instead of local state
4. On initial load, if no `?project=` param exists and projects are loaded, redirect to the first project's URL using `replaceState: true`

---

## Issue 2: Drag-and-drop placeholder boxes instead of lines

**Problem:** Current drop indicators are thin lines (`h-0.5 bg-primary`). User wants placeholder boxes matching the dragged item's dimensions.

**Solution:** Capture the dragged element's dimensions on `dragstart` and render a styled placeholder box of that size at the drop position.

### Changes in `ui/src/lib/components/tasks/KanbanColumn.svelte`

1. Add module-level state for dragged task dimensions
2. In `handleDragStart`, capture the card's dimensions before drag begins
3. Replace the thin line indicators with placeholder boxes

### Changes in `ui/src/lib/components/tasks/KanbanBoard.svelte`

1. Add module-level state for dragged column dimensions
2. Capture column dimensions when column drag starts via callback from KanbanColumn
3. Replace the thin vertical line indicators with placeholder column boxes

## Files modified

1. `ui/src/routes/tasks/+page.svelte` — URL sync for project routing
2. `ui/src/lib/components/tasks/KanbanColumn.svelte` — Capture task drag dimensions, render placeholder boxes for tasks, emit column drag dimensions
3. `ui/src/lib/components/tasks/KanbanBoard.svelte` — Receive column drag dimensions, render placeholder boxes for columns

---

## Implementation Log

### `ui/src/routes/tasks/+page.svelte`
- Imported `goto` from `$app/navigation`
- Changed `selectedProjectId` from `$state('')` to `$derived(page.url.searchParams.get('project') ?? '')`
- Added `selectProject(id)` function that calls `goto('/tasks?project=${id}')`
- Updated project dropdown onclick to use `selectProject()` instead of direct state assignment
- Simplified `loadProjects()` to redirect to first project via `goto()` with `replaceState: true` when no `?project=` param exists

### `ui/src/lib/components/tasks/KanbanColumn.svelte`
- Added `oncolumndragstart` callback prop to emit column dimensions upward
- Added module-level `draggedTaskHeight` state (shared across instances)
- Capture `card.offsetHeight` in `handleDragStart` before setting drag image
- Emit `oncolumndragstart(width, height)` in `handleColumnDragStart`
- Replaced thin line drop indicators (`h-0.5 bg-primary`) with dashed placeholder boxes using `bg-primary/10 border-2 border-dashed border-primary/40 rounded-lg` styled to `draggedTaskHeight`

### `ui/src/lib/components/tasks/KanbanBoard.svelte`
- Added `draggedColumnWidth` and `draggedColumnHeight` state
- Added `handleColumnDragStart(width, height)` callback to receive dimensions from KanbanColumn
- Passed `oncolumndragstart={handleColumnDragStart}` to each KanbanColumn
- Replaced thin vertical line drop indicators (`w-1 bg-primary`) with dashed placeholder boxes using `bg-primary/10 border-2 border-dashed border-primary/40 rounded-lg` styled to captured column dimensions
