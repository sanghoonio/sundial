# Plan: Find Bar + Notes List Search Shortcut

## Files Changed

| File | Action |
|------|--------|
| `ui/src/lib/components/notes/FindBar.svelte` | CREATE |
| `ui/src/lib/stores/notesSearch.svelte.ts` | CREATE |
| `ui/src/routes/notes/[id]/+page.svelte` | MODIFY |
| `ui/src/routes/notes/+layout.svelte` | MODIFY |

## Implementation Log

### Feature 1: Find Bar (`Ctrl/Cmd+F`)

- Created `FindBar.svelte` — VS Code-style floating bar positioned absolute top-right of editor content area
- UI: Search icon | text input (w-48) | match count | ChevronUp | ChevronDown | X close
- Keyboard: Enter = next, Shift+Enter = prev, Escape = close
- Edit mode: finds matches across all md blocks, focuses textarea + setSelectionRange, scrolls block into view
- Preview mode: uses `window.find()` for rendered text highlighting
- Exports `focus()` method for re-focus when Ctrl+F pressed while already open

### Feature 2: Notes List Search Shortcut (`Ctrl/Cmd+Shift+F`)

- Created `notesSearch.svelte.ts` store with `requestKey` counter and `requestFocus()` method
- Wired into layout to call existing `openSearch()` when requestKey increments
- Added `Ctrl/Cmd+Shift+F` handler in note page (checked before plain Ctrl+F)

### Keyboard Handler Order

1. `Ctrl/Cmd+Shift+F` → notesSearch.requestFocus()
2. `Ctrl/Cmd+S` → handleSave()
3. `Ctrl/Cmd+F` → open/focus find bar
4. `Ctrl/Cmd+D` → toggle preview
5. `Ctrl/Cmd+E` → toggle fullscreen
6. `Escape` + findOpen → close find bar
7. `Escape` + fullscreen → exit fullscreen

### Verification

- `svelte-check` passes with 0 errors (1 pre-existing warning unrelated to changes)
