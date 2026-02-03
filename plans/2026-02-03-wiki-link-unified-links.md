# Wiki-Link Parsing & Unified Links UI

## Overview

Fix wiki-link parsing to handle pipe syntax and merge "Linked Items" / "Backlinks" into a single unified "Links" section.

---

## Implementation Log

### 1. Backend: Fix Wiki-Link Parser

**File:** `api/services/link_parser.py`

Updated `parse_links()` to strip display text from pipe syntax before processing:

```python
# Strip display text if pipe syntax used: [[target|display]]
if "|" in raw:
    raw = raw.split("|", 1)[0].strip()
```

**Result:** `[[task:task_abc|Review PR]]` now stores identifier as `task_abc`, not `task_abc|Review PR`

---

### 2. Backend: New Schema Types

**File:** `api/schemas/note.py`

Added new schema types:

- `LinkEventItem` - event info with id, title, start_time, all_day
- `LinksResponse` - consolidated links response with:
  - `outgoing_notes`, `outgoing_tasks`, `outgoing_events` (this note links TO these)
  - `incoming_notes`, `incoming_tasks` (these link TO this note)

---

### 3. Backend: New `/links` Endpoint

**File:** `api/routes/notes.py`

Created new `GET /{note_id}/links` endpoint that returns all links in one call:

**Outgoing links (from this note):**
- Note links from NoteLink where source=this note, link_type='note'
- Task links from NoteLink where link_type='task' (uses target_identifier)
- Event links from NoteLink where link_type='event' + NoteCalendarLink

**Incoming links (to this note):**
- Notes that link to this note (via existing `get_backlinks()`)
- Tasks with `source_note_id` = this note

---

### 4. Frontend: TypeScript Types

**File:** `ui/src/lib/types.ts`

Added:
- `LinkEventItem` interface
- `LinksResponse` interface

---

### 5. Frontend: Unified Links Section

**File:** `ui/src/routes/notes/[id]/+page.svelte`

Replaced separate "Linked Items" and "Backlinks" sections with unified "Links" section:

- Uses new `/links` endpoint instead of `/backlinks`
- Groups by type: Tasks, Events, Notes
- Outgoing links: normal display
- Incoming links: small arrow icon (ArrowUpLeft) indicator
- Removed `linkedEventDetails` state (now fetched via links endpoint)

---

## Files Changed

| File | Changes |
|------|---------|
| `api/services/link_parser.py` | Handle pipe syntax in `parse_links()` |
| `api/schemas/note.py` | Add `LinkEventItem`, `LinksResponse` |
| `api/routes/notes.py` | Add imports, create `/links` endpoint |
| `ui/src/lib/types.ts` | Add `LinkEventItem`, `LinksResponse` |
| `ui/src/routes/notes/[id]/+page.svelte` | Unified Links UI, use `/links` endpoint |

---

## Verification Steps

1. Create a note with wiki-links: `[[task:task_xxx|Task Title]]`, `[[Another Note]]`
2. Save the note
3. Check NoteLink records in database - identifier should be `task_xxx` not `task_xxx|Task Title`
4. View note detail - Links section should show the task and note
5. View the linked note - should show incoming link from the first note
