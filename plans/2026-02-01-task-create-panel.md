# Plan: Replace Task Create Modal with Sidebar Panel on Notes Page

## Overview

Replace the `TaskCreateModal` dialog on the notes detail page with a right-side sidebar panel, matching the pattern used by `TaskDetailPanel` in the tasks view.

## Implementation Log

### Files Changed

1. **`ui/src/lib/components/tasks/TaskCreatePanel.svelte`** (new)
   - Created sidebar panel component styled like `TaskDetailPanel` (`w-96 shrink-0 border-l`)
   - Props: `projectId`, `projects`, `sourceNoteId`, `onclose`, `oncreated`
   - Form fields: title, description, project selector, priority, due date, milestone, checklist
   - Explicit "Create" button (no auto-save since task doesn't exist yet)
   - Cmd/Ctrl+Enter shortcut to create, Escape to close
   - Source note indicator badge when `sourceNoteId` is set

2. **`ui/src/routes/notes/[id]/+page.svelte`**
   - Replaced `TaskCreateModal` import with `TaskCreatePanel`
   - Wrapped existing content in a `flex h-full` outer container
   - Note content area now wrapped in `flex-1 flex flex-col min-w-0`
   - Panel renders conditionally alongside content when `createTaskOpen` is true
   - Note content shrinks to accommodate panel (not overlaid)

### Verification

- `npm run build` passes with no new warnings
