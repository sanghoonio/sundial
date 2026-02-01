# Project Detail Page → Context Hub

## Goal

Repurpose `/projects/[id]` from a Kanban board duplicate into a project context hub that ties notes, tasks, and milestones together. The tasks page remains the only Kanban interface.

## Changes

### 1. Rewrite `/projects/[id]/+page.svelte`

**Removed:** KanbanBoard, TaskDetailPanel, TaskCreateModal, settings modal, all drag/drop handlers, column management handlers, task selection state.

**Replaced with a scrollable single-column layout:**

- **Header bar** — Back button, project color dot, name, status badge, task counter (`5/12`), metadata toggle button (Info icon)
- **Metadata panel** (collapsible `{#if showMeta}`) — Editable name, description, color, status. Created/updated timestamps. Save button. Delete project button.
- **Task progress section** — Overall progress bar with percentage. "Open in Kanban" link to `/tasks?project={id}`.
- **Milestones section** — Grid of small cards with milestone name, task count (`done/total`), mini progress bar. Read-only.
- **Notes section** — List of notes linked to this project (from `GET /api/notes?project_id={id}`). Each row: title, tags (max 2), updated date. Links to `/notes/{id}`. "New Note" button links to `/notes/new?project={id}`.
- **Recent tasks section** — Last 5 updated tasks using `TaskCard` compact mode. No click handler.

Content area uses `max-w-3xl mx-auto` for readable width on desktop.

### 2. Add query param support to `/tasks/+page.svelte`

Read `?project=` from URL in `loadProjects()`. If the param matches a project ID, pre-select it instead of defaulting to the first project.

### 3. Add query param support to `/notes/new/+page.svelte`

Read `?project=` from URL and pre-fill the `projectId` state so the project selector is pre-selected when creating a note from the project hub.

## Files Changed

| File | Change |
|------|--------|
| `ui/src/routes/projects/[id]/+page.svelte` | Full rewrite (305 lines replacing 357) |
| `ui/src/routes/tasks/+page.svelte` | Added `?project=` query param reading (~5 lines) |
| `ui/src/routes/notes/new/+page.svelte` | Added `?project=` query param reading (~2 lines) |

## Implementation Log

- Rewrote project detail page as context hub with all sections from plan
- Added `page` import and query param reading to tasks page `loadProjects()`
- Initialized `projectId` from URL search params in notes/new page
- `svelte-check` passes with 0 errors
