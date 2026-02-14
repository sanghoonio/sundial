---
date: 2026-02-14
status: complete
description: Implement slide and float toolbar modes for the markdown editor with an appearance setting
---

# Editor Toolbar Style Setting

## Context

When clicking into a markdown block, the `MarkdownToolbar` is conditionally rendered inline with `{#if focused}` inside an `overflow-hidden` container (`MarkdownBlock.svelte:453-457`). This inserts ~32px into flow and pushes the textarea down instantly — the text you're about to edit shifts from under your cursor.

We'll implement two toolbar modes and let the user choose via the Appearance settings page:

- **Slide** (default): toolbar animates open inline using Svelte's `slide` transition (~150ms). Content still shifts but smoothly.
- **Float**: toolbar positioned absolutely above the block border with a fade+fly animation. Zero content shift, but overlaps content above (including the AddBlockDivider).

## Changes

### 1. Backend — add `editor_toolbar_style` setting

**`api/schemas/settings.py`** — add field to both models:
- `SettingsResponse`: `editor_toolbar_style: str = "slide"`
- `SettingsUpdate`: `editor_toolbar_style: str | None = None`

**`api/routes/settings.py`** — add to `_SETTINGS_KEYS`:
- `"editor_toolbar_style": ("str", "slide")`

### 2. Frontend types

**`ui/src/lib/types.ts`** — add to both interfaces:
- `SettingsResponse`: `editor_toolbar_style: string`
- `SettingsUpdate`: `editor_toolbar_style?: string`

### 3. Appearance settings page

**`ui/src/routes/settings/appearance/+page.svelte`**

- Add `editorToolbarStyle` state variable, load from API in `loadSettings()`
- Add a select dropdown with options "Slide" / "Float"
- Include in `handleSave()` update payload
- Write to `localStorage.setItem('sundial_editor_toolbar_style', ...)` on save (for fast component reads)

### 4. MarkdownBlock — implement both toolbar rendering modes

**`ui/src/lib/components/notes/MarkdownBlock.svelte`**

Add import: `import { slide, fly, fade } from 'svelte/transition';`

Read preference: `const toolbarStyle = localStorage.getItem('sundial_editor_toolbar_style') ?? 'slide';`

Replace the current `{#if focused}` toolbar block (lines 453-457) with:

```svelte
{#if focused && toolbarStyle === 'float'}
  <!-- Float mode: absolute positioned above block border -->
  <div
    class="absolute bottom-full left-0 right-0 mb-1 z-10"
    in:fly={{ y: 4, duration: 150 }}
    out:fade={{ duration: 100 }}
  >
    <div class="px-2 py-1 bg-base-200 rounded-lg border border-base-content/20 shadow-sm">
      <MarkdownToolbar textarea={textareaEl} />
    </div>
  </div>
{/if}

<div class="w-full overflow-hidden rounded-lg border border-base-content/20 {focused ? 'shadow-...' : ''}">
  {#if focused && toolbarStyle === 'slide'}
    <!-- Slide mode: inline with animated expand -->
    <div transition:slide={{ duration: 150 }}>
      <div class="px-2 py-1 bg-base-200/50 border-b border-base-content/20">
        <MarkdownToolbar textarea={textareaEl} />
      </div>
    </div>
  {/if}
  <!-- textarea wrapper (unchanged) -->
</div>
```

Key details:
- **Float mode**: toolbar is a sibling BEFORE the `overflow-hidden` div (so it's not clipped), positioned via `absolute bottom-full` on the already-`relative` wrapper. Fully opaque `bg-base-200`, own `rounded-lg` border, `shadow-sm`, `z-10`.
- **Slide mode**: toolbar stays inline inside the border container (current position). Wrapped in `transition:slide` for smooth height animation. Content shifts gradually over 150ms.
- `toolbarStyle` read from localStorage once on component init — no prop threading needed. Updates take effect on next navigation to a note.

## Files modified

| File | Change |
|------|--------|
| `api/schemas/settings.py` | Add `editor_toolbar_style` to response + update schemas |
| `api/routes/settings.py` | Add to `_SETTINGS_KEYS` dict |
| `ui/src/lib/types.ts` | Add to TS interfaces |
| `ui/src/routes/settings/appearance/+page.svelte` | Add toolbar style dropdown + localStorage write |
| `ui/src/lib/components/notes/MarkdownBlock.svelte` | Implement both toolbar rendering modes with transitions |

## Verification

1. **Slide mode** (default): open a note, click a text block — toolbar should smoothly slide open, pushing content down over ~150ms
2. **Float mode**: change setting in Appearance, navigate to a note, click a block — toolbar should appear floating above the block border with no content shift
3. **Toolbar function**: in both modes, bold/italic/heading/etc. buttons should work correctly
4. **Mode switching**: change setting in Appearance → Save → navigate to notes → new mode applies
5. **Persistence**: reload the browser — setting should persist (localStorage + database)
6. **Mobile**: both modes should render correctly on narrow viewports
