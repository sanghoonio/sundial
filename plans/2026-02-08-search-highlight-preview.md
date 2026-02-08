# Fix search highlighting in notes preview mode

## Plan

Ctrl+F search in notes highlights matches in edit mode using a backdrop overlay with `<mark>` tags, but in preview mode it fell back to `window.find()` which only selects one match at a time with no persistent highlighting. The goal was to highlight all matches in preview mode with the current match visually distinct.

### Approach: DOM-based text node highlighting in preview

Inject `<mark>` elements into the preview DOM by walking text nodes after render, avoiding fragile HTML string manipulation.

### Files modified

1. **`ui/src/lib/components/notes/MarkdownBlock.svelte`** — Added `highlightPreviewEl()` and `clearPreviewHighlights()` helpers, `currentMatchOrdinal` derived, and `$effect` to apply/cleanup highlights
2. **`ui/src/lib/components/notes/FindBar.svelte`** — Replaced `window.find()` with `mark.find-match.current` scroll + block flash
3. **`ui/src/app.css`** — Added `mark.find-match` and `mark.find-match.current` styles

## Implementation Log

- Added `clearPreviewHighlights(el)`: unwraps all `mark.find-match` elements back to text nodes, then `normalize()`
- Added `highlightPreviewEl(el, query, currentOrdinal)`: uses `TreeWalker(SHOW_TEXT)` to collect text nodes, finds case-insensitive matches, splits and wraps in `<mark class="find-match [current]">`
- Added `currentMatchOrdinal` derived that counts occurrences in raw content before `currentMatch.start` to determine which `<mark>` gets the `current` class
- Added `$effect` gated on `preview && previewEl` that calls highlighting via `queueMicrotask` (to run after rendered HTML is in DOM) with cleanup
- Updated FindBar's `goToMatch` preview branch to query for `mark.find-match.current` and `scrollIntoView({ block: 'center', behavior: 'smooth' })` plus block flash highlight
- Added CSS: `mark.find-match` with `oklch(var(--wa) / 0.2)` background, `.current` variant at `0.5` opacity
- `svelte-check`: 0 errors
