# Fix: Theme default, dashboard mobile, task project reactivity, note task links

## Bugs Fixed

### Bug 1: Theme auto-detection removed
- **Sidebar.svelte**: Removed `matchMedia` fallback; `darkMode = stored === 'dark'` defaults to light
- **app.css**: Removed `--prefersdark` from DaisyUI config

### Bug 2: Dashboard mobile column height
- **+page.svelte**: Changed `h-[calc(100vh-4rem)]` to `min-h-0 md:h-[calc(100vh-4rem)]`

### Bug 3: Task project change reactivity
- **tasks/[projectId]/+page.svelte**: `handleTaskSaved` now filters out task when `project_id !== selectedProjectId`

### Bug 4: Note task links navigate to correct project
- **api/schemas/note.py**: Added `project_id: str` to `BacklinkTaskItem`
- **api/routes/notes.py**: Added `project_id=t.project_id` to all 3 `BacklinkTaskItem` constructions
- **ui/src/lib/types.ts**: Added `project_id: string` to `BacklinkTaskItem`
- **ui/src/routes/notes/[id]/+page.svelte**: Changed task link hrefs to include `{task.project_id}`
- **ui/src/routes/tasks/+page.svelte**: Redirect fetches task to resolve correct `project_id`

## Implementation Log
- All 4 bugs implemented in a single pass
- No new files created; all changes are edits to existing files
