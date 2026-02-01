# Plan: UI–API Parity for Notes/Tasks/Events Connections

## Gap Summary

The API supports rich cross-entity linking that the UI didn't fully expose:

| Connection | API | UI Status |
|---|---|---|
| Task → Note (`source_note_id`) | Create-only field | **Read-only generic text** in detail panels; **not settable** from any UI |
| Task → Event (`calendar_event_id`) | Create-only field | **Read-only generic text**; **not settable** from any UI |
| Note → Events (`linked_events`) | Returns event IDs | Shows **count only** ("N linked event(s)") |
| Event → Notes/Tasks (`linked_notes`, `linked_tasks`) | Returns full refs (id+title+status) | **Completely ignored** by EventPanel |
| Create task from note/event context | API accepts both IDs on POST | **No UI path** for this |

## Changes (6 files)

### 1. `ui/src/lib/types.ts`
- Added `LinkedNoteRef` and `LinkedTaskRef` interfaces
- Added `linked_notes` and `linked_tasks` to `EventResponse`

### 2. `ui/src/lib/components/tasks/TaskCreateModal.svelte`
- Added `sourceNoteId` and `calendarEventId` optional props
- Included them in the `TaskCreate` payload
- Shows read-only indicator above Create button when linked

### 3. `ui/src/routes/notes/[id]/+page.svelte`
- Added "Create task" button in Linked Items section header
- Opens TaskCreateModal with `sourceNoteId` pre-set
- Fetches linked event details (title + date) instead of showing count
- Always shows Linked Items section (even when empty)
- Refreshes backlinks after task creation

### 4. `ui/src/lib/components/calendar/EventPanel.svelte`
- Shows linked notes and tasks with titles in a "Linked Items" section
- "Create linked task" button for existing events
- Re-fetches event after task creation to update display

### 5. `ui/src/lib/components/tasks/TaskDetailPanel.svelte`
- Fetches actual note/event titles via $effect
- Displays titles instead of generic "Linked note" / "Calendar event"
- Changed layout from horizontal to vertical for readability

### 6. `ui/src/lib/components/tasks/TaskDetailModal.svelte`
- Same pattern as TaskDetailPanel for title fetching and display

## Implementation Log

All 6 file changes implemented and verified. `npm run build` passes cleanly.
