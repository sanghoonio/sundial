# Notes: macOS-Style Split-Pane Layout

## Plan

Replace the card grid + separate pages approach with a persistent left list / right editor split pane.

- Left pane: scrollable note list with search, tag filter, sort
- Right pane: selected note editor, new note form, or empty state
- Uses SvelteKit nested layout (`/routes/notes/+layout.svelte`) so the list persists across note selections

## Implementation Log

### Files Created
- `src/lib/stores/noteslist.svelte.ts` — Refresh signal store (`notesList.refresh()` / `notesList.refreshKey`)
- `src/lib/components/notes/NoteListItem.svelte` — Compact list row with title, date, preview, tag badges, selected highlight
- `src/routes/notes/+layout.svelte` — Split-pane shell: left list (w-72/lg:w-80) + right `{@render children()}`

### Files Modified
- `src/routes/+layout.svelte` — Added `relative` class to `<main>` so notes layout can use `absolute inset-0`
- `src/routes/notes/+page.svelte` — Replaced card grid with centered empty state ("Select a note" + new note button)
- `src/routes/notes/[id]/+page.svelte` — Removed full-width back button (mobile-only now), replaced `max-w-3xl mx-auto` with `p-4 md:p-6 max-w-4xl`, added `notesList.refresh()` on save/delete
- `src/routes/notes/new/+page.svelte` — Removed cancel link, added mobile-only back button, replaced wrapper, added `notesList.refresh()` on create

### Mobile Behavior
- Left pane hidden when a note or new-note is selected; right pane hidden on index
- Mobile-only back button (`md:hidden`) on editor and new-note pages

### Build
- `npm run build` passes with no errors
