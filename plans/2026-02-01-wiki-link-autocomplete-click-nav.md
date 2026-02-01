# Wiki-Link Autocomplete + Click Navigation

## Plan

1. Create `WikiLinkSuggest.svelte` — floating autocomplete dropdown for `[[` wiki-links
2. Update `MarkdownBlock.svelte` — autocomplete trigger, keyboard interception, preview click navigation

## Implementation Log

### New: `ui/src/lib/components/notes/WikiLinkSuggest.svelte`

- Fetches notes from `/api/notes?search=<query>&limit=8` with 200ms debounce
- Keyboard navigation: ArrowUp/Down to move, Enter to select, Escape to close
- `export function handleKey()` for parent to forward keyboard events
- Click-outside closes the dropdown
- Uses `onmousedown` with `preventDefault` to avoid textarea blur before selection

### Modified: `ui/src/lib/components/notes/MarkdownBlock.svelte`

**Autocomplete trigger (`checkForWikiLink`):**
- On every input, scans backwards from cursor for `[[` with no intervening `]]` or newlines
- Sets `suggestActive`, `suggestQuery`, and `suggestPosition`

**Cursor position measurement (`measureCursorPosition`):**
- Creates a hidden mirror `<div>` matching textarea styles
- Inserts a `<span>` marker at the `[[` position to get pixel coordinates
- Returns position relative to the editor wrapper

**Keyboard interception:**
- When `suggestActive`, forwards ArrowUp/Down/Enter/Escape to `WikiLinkSuggest.handleKey()`
- If handled, skips the existing list-continuation logic

**Selection callback (`handleSuggestSelect`):**
- Finds `[[` position, replaces range with `[[Title]]` using `setRangeText`
- Dispatches input event, closes suggestions, refocuses textarea

**Preview click handler (`handlePreviewClick`):**
- Listens for clicks on `a.wiki-link-note` elements in preview mode
- Extracts `data-title`, searches notes API for exact title match
- Navigates to `/notes/<id>` via `goto()`

### Build

`npm run build` passes. No new warnings introduced.
