# Tasks & Projects Frontend Polish

## Context

Backend APIs for tasks and projects are fully implemented. The frontend has basic kanban, task cards, project list/detail, and task modals — but it's significantly less polished than the notes feature. No blocking dependencies exist; we can work on tasks and projects directly.

## Plan: 6 Phases

### Phase 1: Task Card Enhancements
- Description preview (1-2 lines, `line-clamp-2`) on cards
- Due date badge with overdue styling (`badge-error` when past due)
- Priority indicator as colored left border (`border-l-2`)
- Checklist progress bar replacing plain "X/Y items" text
- Linked note icon (`StickyNote`) and calendar event icon (`CalendarDays`) when present
- AI suggestion styling (dashed border + accept/dismiss) per spec
- Empty state in columns when no tasks exist

### Phase 2: Task Detail Modal Overhaul
- Add status field (open/in_progress/done) with selector
- Add milestone selector (requires passing milestones from parent)
- Linked note and calendar event display with clickable links
- Improved checklist: inline editing, Enter to add next, progress bar at top
- Created/updated timestamps at bottom
- Wider modal (`max-w-2xl`) for better editing space

### Phase 3: Task Filtering, Sorting & Search
- Search input (debounced, matches notes pattern)
- Priority filter dropdown
- Due date filter: All / Overdue / Due today / Due this week / No date
- Sort by: position, due date, priority, created date (asc/desc)
- Client-side filtering using `$derived.by()`
- Filtered count badge

### Phase 4: Better Task Creation
- Full creation modal: title, description, priority, due date, milestone, checklist
- Cmd/Ctrl+Enter to submit
- Quick-add keeps working for title-only; expand button opens full modal
- Wire up in both tasks page and project detail page

### Phase 5: Projects Page Polish
- Status filter chips on project list (All / Active / Paused / Completed / Archived)
- Project color accent (left border on cards, dot in header)
- Inline status change dropdown on project cards
- Project detail header: color dot, status badge, task stats (count + completion %)
- Settings modal: add color picker, status selector, milestone reorder arrows

### Phase 6: Drag-and-Drop & Cross-cutting
- Drop indicator line between cards
- Opacity on dragged card
- Optimistic reordering (revert on API failure)
- Proper position calculation
- Keyboard shortcuts: `n` quick-add, `Shift+N` full modal, `/` focus search
- Mobile kanban: scroll snap, full-width columns on small screens
- Empty state when no projects exist

## Implementation Log

_Started: 2026-01-31_

### Phase 1: Task Card Enhancements — Done
- `TaskCard.svelte`: Added `border-l-2` priority border colors, description preview with `line-clamp-2`, due date badge with `badge-error` for overdue, checklist progress bar with percentage, linked note/event icons (`StickyNote`/`CalendarDays`), AI suggestion styling with dashed border + accept/dismiss buttons
- `KanbanColumn.svelte`: Added empty state with `Inbox` icon when no tasks

### Phase 2: Task Detail Modal Overhaul — Done
- `TaskDetailModal.svelte`: Added status selector (open/in_progress/done), milestone selector (accepts milestones prop from parent), linked note/event clickable links, inline checklist editing (double-click + Enter to advance), progress bar at top of checklist, created/updated timestamps at bottom
- `Modal.svelte`: Added `size` prop (`default`/`wide`/`full`) for wider modal support
- Updated both `tasks/+page.svelte` and `projects/[id]/+page.svelte` to pass milestones to modal

### Phase 3: Task Filtering, Sorting & Search — Done
- **New file:** `TaskFilterBar.svelte` — search input, priority filter, due date filter (all/overdue/today/this week/no date), sort by (position/due date/priority/created), ascending/descending toggle, filtered count badge
- `tasks/+page.svelte`: Client-side filtering using `$derived.by()`, keyboard shortcut `/` to focus search

### Phase 4: Better Task Creation — Done
- **New file:** `TaskCreateModal.svelte` — full creation form with title, description, priority, due date, milestone, checklist; Cmd/Ctrl+Enter to submit
- `TaskQuickAdd.svelte`: Added expand button that triggers `onfullcreate` callback to open full modal
- `KanbanBoard.svelte`: Passes `onfullcreate` through to columns
- `KanbanColumn.svelte`: Passes `onfullcreate` to TaskQuickAdd
- Wired up `TaskCreateModal` in both tasks page and project detail page

### Phase 5: Projects Page Polish — Done
- `projects/+page.svelte`: Status filter chips (all/active/paused/completed/archived) with counts, color accent left border on cards, inline status change dropdown (optimistic update), color picker in create modal with preset swatches, empty state with icon
- `projects/[id]/+page.svelte`: Color dot + status badge in header, task stats (count + completion %), overall progress bar, settings modal with status selector + color picker + milestone reorder arrows (ChevronUp/ChevronDown)

### Phase 6: Drag-and-Drop & Cross-cutting — Done
- `KanbanColumn.svelte`: Drop indicator line between cards based on mouse Y position, opacity on dragged card (0.4), proper dragLeave handling (only when leaving column), full-width columns on mobile (`w-[calc(100vw-3rem)]`)
- `KanbanBoard.svelte`: `snap-x snap-mandatory` for mobile scroll snapping
- Tasks page: Optimistic reordering with rollback on API failure, keyboard shortcuts (`/` focus search, `Shift+N` full create modal)
- Project detail: Optimistic drag-and-drop with rollback

### Files Modified
- `ui/src/lib/components/tasks/TaskCard.svelte` — rewritten
- `ui/src/lib/components/tasks/KanbanColumn.svelte` — rewritten
- `ui/src/lib/components/tasks/KanbanBoard.svelte` — rewritten
- `ui/src/lib/components/tasks/TaskQuickAdd.svelte` — rewritten
- `ui/src/lib/components/tasks/TaskDetailModal.svelte` — rewritten
- `ui/src/lib/components/ui/Modal.svelte` — size prop added
- `ui/src/routes/tasks/+page.svelte` — rewritten with filters + create modal
- `ui/src/routes/projects/+page.svelte` — rewritten with filters + polish
- `ui/src/routes/projects/[id]/+page.svelte` — rewritten with header + create modal

### Files Created
- `ui/src/lib/components/tasks/TaskFilterBar.svelte`
- `ui/src/lib/components/tasks/TaskCreateModal.svelte`

### Build Status
- `svelte-check`: 0 errors, 3 warnings (all pre-existing)
- `npm run build`: success
