# Plan: New Note Untitled Save, Dblclick Fix, Cross-Links, Settings Cleanup

## 1. New Note: Save with "Untitled" when no title

**Files:** `ui/src/routes/notes/new/+page.svelte`

- `hasContent()` — only check if blocks have content (removed title requirement)
- `handleCreate()` — use `title.trim() || 'Untitled'` instead of bailing on empty title
- Save button `disabled` — use `!hasContent()` instead of `creating || !title.trim()`

## 2. Fix double-click preview toggle

**Files:** `ui/src/lib/components/notes/MarkdownBlock.svelte`

- Removed `ondblclick={handleDblClick}` from edit-mode outer div
- Kept it on the preview div only — double-click rendered markdown to switch to edit

## 3. Notes/Tasks cross-linking

### 3A. Backend: Populate `linked_tasks` on note responses

**Files:** `api/routes/notes.py`

- Made `_note_to_response()` and `_note_to_list_item()` async with `db: AsyncSession` param
- Query `Task.id` where `Task.source_note_id == note.id` for linked_tasks
- Also populated linked_events in list items from calendar_links
- Updated all callers to await and pass db

### 3B. Frontend: Enrich linked items on note detail page

**Files:** `ui/src/routes/notes/[id]/+page.svelte`

- Used `backlinks.tasks` data to show task names with status badges and links
- Falls back to count display if backlinks data not available

### 3C. Frontend: Task count badge on NoteListItem

**Files:** `ui/src/lib/components/notes/NoteListItem.svelte`

- Shows task count badge when `note.linked_tasks.length > 0`

## 4. Settings page UI cleanup

**Files:** `ui/src/routes/settings/+page.svelte`

- Replaced `<label class="label"><span class="label-text">` with `<p>` tags
- Removed all `a11y_label_has_associated_control` ignores
- Tightened CalDAV nested section padding (pl-2 → pl-3)
- Made save button sticky at bottom with border-top

---

## Implementation Log

All 5 tasks completed. `npm run build` passes successfully.
