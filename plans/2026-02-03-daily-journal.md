# Daily Journal Feature

## Overview

Add a "Daily Journal" feature that creates context-aware journal entries summarizing the user's day - notes taken, tasks added/completed, and events that happened. Optionally AI-assisted to generate reflective content.

---

## Implementation Log

### Backend: `GET /api/dashboard/journal-data`

Added new endpoint in `api/routes/dashboard.py`:

- **JournalDataResponse** schema with:
  - `date` - the current date
  - `notes_created` - notes created today
  - `notes_updated` - notes updated today (excluding those created today)
  - `tasks_created` - tasks created today
  - `tasks_completed` - tasks completed today (using `completed_at` field)
  - `events` - calendar events that occurred today

### Frontend: Split Button UI

Updated `ui/src/routes/notes/+layout.svelte`:

- Replaced standalone "New Note" button and "NoteImportButton" with a split button group
- Main button: Plus icon linking to `/notes/new`
- Dropdown button with ChevronDown icon containing:
  - "Daily journal" - creates a new journal note with today's activity
  - "Import markdown" - triggers file picker for markdown import

### Frontend: Journal Creation

Added client-side logic in `ui/src/routes/notes/+layout.svelte`:

- `createJournal()` - fetches journal data from API and creates note
- `generateJournalTemplate()` - builds markdown template with:
  - Title: "Daily Journal - {formatted date}"
  - Events section with times
  - Tasks completed section with wiki-links `[[task:id|title]]`
  - Tasks added section with wiki-links
  - Notes updated section with wiki-links `[[title]]`
  - Notes created section with wiki-links
  - "No recorded activity" message if empty day
  - Reflections section for user to write in
- Tags: `["journal", "daily"]`

### Cleanup

- Deleted `ui/src/lib/components/notes/NoteImportButton.svelte` (functionality moved inline)

### Files Changed

1. `api/routes/dashboard.py` - Added `JournalDataResponse` schema and `GET /journal-data` endpoint
2. `ui/src/routes/notes/+layout.svelte` - Split button UI, import logic, journal creation logic
3. Deleted: `ui/src/lib/components/notes/NoteImportButton.svelte`
