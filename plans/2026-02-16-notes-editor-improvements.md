---
date: 2026-02-16
status: complete
description: Improve notes editor to be on par with GitHub's markdown editor
---

# Notes Editor Improvements

## Context

The notes editor has several bugs and is missing features that GitHub's editor provides as standard. The user-reported issues are: (1) auto-numbering always starts at 1, (2) no keyboard shortcuts for bold/italic/etc, (3) toggling formatting doesn't remove it, (4) missing toolbar buttons. Beyond those, there's a meaningful feature gap with GitHub's editor around strikethrough, task lists, smart paste, and code blocks. Underline is excluded — it's non-standard markdown and the `<u>` HTML tags look ugly in the raw editor.

## Changes

### 1. Extract shared formatting utilities (NEW FILE)

**File:** `ui/src/lib/utils/editorFormatting.ts`

Extract `wrap()`, `insertAtLineStart()`, and `insertText()` from MarkdownToolbar into a shared module so both the toolbar (click) and MarkdownBlock (keyboard shortcuts) can use them without duplication. Each function takes `{textarea, onchange}` instead of using closure variables.

### 2. Fix `wrap()` toggle behavior

**File:** `ui/src/lib/utils/editorFormatting.ts`

Current `wrap()` always adds markers. New logic checks two cases before wrapping:
- **Selection includes markers**: e.g. user selected `**bold**` — strip the markers
- **Markers surround selection**: e.g. cursor is inside `**|bold|**` — remove surrounding markers

Otherwise wrap as normal. This gives toggle behavior for bold, italic, strikethrough, and inline code.

### 3. Fix auto-numbering starting at 1

**File:** `ui/src/lib/utils/editorFormatting.ts` (in `insertAtLineStart`)

Currently `${i + 1}. ${line}` uses the array index. Fix: look at the line preceding the selection block, extract its number with regex, and continue from `prevNum + 1`. Falls back to 1 if no preceding numbered line.

### 4. Add 4 new toolbar buttons

**File:** `ui/src/lib/components/notes/MarkdownToolbar.svelte`

| Button | Icon | Handler | Syntax |
|--------|------|---------|--------|
| Strikethrough | `Strikethrough` | `wrap('~~', '~~')` | `~~text~~` |
| Task list | `ListChecks` | `insertAtLineStart('- [ ] ')` | `- [ ] item` |
| Code block | `Braces` | `insertText('\n```\n\n```\n')` | fenced code block |
| Image | `ImagePlus` | `wrap('![', '](url)')` | `![alt](url)` |

Import from shared utils, add handlers, add buttons in logical groups with dividers.

### 5. Add keyboard shortcuts for formatting

**File:** `ui/src/lib/components/notes/MarkdownBlock.svelte`

Add in `handleKeydown`, before existing Tab handling:

| Shortcut | Action |
|----------|--------|
| Cmd+B | Bold (`**`) |
| Cmd+I | Italic (`*`) |
| Cmd+`` ` `` | Inline code (`` ` ``) |
| Cmd+K | Link (`[]()`) |
| Cmd+Shift+S | Strikethrough (`~~`) |

### 6. Resolve keyboard shortcut conflicts

**File:** `ui/src/routes/notes/[id]/+page.svelte`

- **Cmd+I**: Currently toggles metadata panel. Reassign to **Cmd+M** ("M" for metadata). Frees Cmd+I for italic. Update the button tooltip to say "Note info (Ctrl+M)".
- **Cmd+E**: Keep as preview toggle. Inline code uses Cmd+`` ` `` instead, so no conflict.

### 7. Hide float toolbar when find bar is open

**File:** `ui/src/lib/components/notes/MarkdownBlock.svelte`

The float toolbar (line 495) shows when `focused && hovered && toolbarStyle === 'float'`. When Cmd+F opens the find bar, the toolbar overlaps it. Fix: add `&& !findActive` to the float toolbar visibility condition. `findActive` is already derived (line 110) from `notesSearch.findQuery`.

### 8. Smart paste (URL on selected text creates link)

**File:** `ui/src/lib/components/notes/MarkdownBlock.svelte`

Add `onpaste` handler to textarea. When text is selected and clipboard contains a valid URL (checked via `new URL()`), `preventDefault()` and insert `[selected](url)` instead. Simple `isUrl()` helper checks for http/https protocol.

## Files Modified

1. `ui/src/lib/utils/editorFormatting.ts` — **NEW**: shared wrap/insertAtLineStart/insertText with toggle + numbering fixes
2. `ui/src/lib/components/notes/MarkdownToolbar.svelte` — import shared utils, add 4 buttons + icons
3. `ui/src/lib/components/notes/MarkdownBlock.svelte` — keyboard shortcuts, smart paste handler
4. `ui/src/routes/notes/[id]/+page.svelte` — reassign Cmd+I to Cmd+M

**Wiki link / backlink compatibility**: Verified no conflicts. Toggle `wrap()` only matches exact marker pairs (won't match `[[`/`]]`). Keyboard shortcuts require Cmd/Ctrl so they don't interfere with `[[` typing. WikiLinkSuggest's key handler takes priority in `handleKeydown` when active. Smart paste creates `[text](url)` not `[[]]`. Existing wiki link button and autocomplete are untouched.

No changes needed to `markdown.ts` — confirmed that `marked` GFM handles `~~strikethrough~~` and task lists. DOMPurify defaults allow `del`, `input` tags.

## Implementation Order

1. Create `editorFormatting.ts` (foundation for everything)
2. Update `MarkdownToolbar.svelte` (import utils, add buttons)
3. Update `MarkdownBlock.svelte` (keyboard shortcuts + smart paste)
4. Update `[id]/+page.svelte` (shortcut conflict fixes)

## Verification

1. Open a note in edit mode
2. Test each toolbar button: bold, italic, strikethrough, code, heading, lists, task list, blockquote, link, wiki link, image, code block, hr
3. Test toggle: select bolded text `**hello**`, click bold — should become `hello`
4. Test toggle: place cursor inside `**hello**` (select just `hello`), press Cmd+B — should remove surrounding `**`
5. Test keyboard shortcuts: Cmd+B, Cmd+I, Cmd+`, Cmd+K, Cmd+Shift+S
6. Test auto-numbering: create a numbered list starting at 5, select new lines below, click numbered list — should continue from 6
7. Test smart paste: select text, paste a URL — should create `[text](url)`
8. Test Cmd+I does italic (not metadata panel); Cmd+M toggles metadata
9. Switch to preview mode and verify all formatting renders correctly (especially ~~strikethrough~~ and task lists)
