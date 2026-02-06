# Fix Notes Page UI Bugs

## Date: 2026-02-06

## Bugs Fixed

### Bug 1: Notes list flashing on every save/autosave
- Added `patchNote()` method to `noteslist.svelte.ts` store with a `_patchedNote` signal
- Layout watches `patchedNote` and updates the matching item in-place (no loading spinner, no API call)
- `handleSave()` now constructs a `NoteListItem` from the save response and calls `patchNote()`
- Tags refresh (`loadTags()`) still happens after patch for sidebar count updates
- `refresh()` kept for delete, import, and journal creation

### Bug 2: New note autosave clears undo history
- Consolidated `/notes/new` and `/notes/[id]` into single `[id]/+page.svelte`
- When `id === 'new'`: skip API fetch, show editor immediately, run auto-create timer
- After creation: `goto('/notes/{realId}', { replaceState: true })` keeps component mounted
- `justCreated` flag prevents re-fetching note data after URL change
- Deleted `routes/notes/new/+page.svelte`

### Bug 3: Edit/preview toggle clears undo history
- Replaced `{#if preview}...{:else}` conditional in `MarkdownBlock.svelte`
- Both preview div and editor div now always rendered, toggled with `class:hidden`
- Textarea stays in DOM at all times, preserving browser undo stack

### Bug 4: Backlinks don't update on save
- Added `links = await api.get(...)` after successful save in `handleSave()`

### Bug 5: Project filter dropdown doesn't close after selection
- Added `(document.activeElement as HTMLElement)?.blur()` to both "All projects" and per-project onclick handlers

## Files Modified
- `ui/src/lib/stores/noteslist.svelte.ts` — Added patchNote mechanism
- `ui/src/routes/notes/+layout.svelte` — Patch effect, isNewNote update, dropdown blur
- `ui/src/routes/notes/[id]/+page.svelte` — Create mode, patchNote in save, links re-fetch
- `ui/src/lib/components/notes/MarkdownBlock.svelte` — Always-mounted textarea
- `ui/src/routes/notes/new/+page.svelte` — Deleted
