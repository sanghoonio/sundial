# Plan: LaTeX Rendering + Fullscreen Mode for Notes

## Implementation Log

### Feature 1: LaTeX Rendering — DONE

1. **Installed deps**: `npm install katex marked-katex-extension` in `ui/`
2. **Registered KaTeX extension** in `ui/src/lib/utils/markdown.ts`:
   - Imported `markedKatex` from `marked-katex-extension`
   - Called `marked.use(markedKatex({ throwOnError: false }))` after wiki-link extension
3. **Updated DOMPurify config** to allow KaTeX output:
   - Added MathML elements (`math`, `semantics`, `mrow`, `mi`, `mo`, `mn`, etc.) to `ADD_TAGS`
   - Added SVG elements (`svg`, `line`, `path`, `rect`, `g`) to `ADD_TAGS`
   - Added `style`, `aria-hidden`, SVG attrs, and `xmlns` to `ADD_ATTR`
4. **Imported KaTeX CSS** in `ui/src/app.css` — `@import 'katex/dist/katex.min.css'`
5. **Added display math styles** — `.prose .katex-display` with vertical margin and horizontal overflow scroll
6. **Updated `markdownPreview()`** to strip `$$...$$` → `[math]` and `$...$` → inner text

### Feature 2: Fullscreen Mode — DONE

1. **Created fullscreen store** at `ui/src/lib/stores/fullscreen.svelte.ts`:
   - Module-level `$state(false)` with `{ get active, toggle(), exit() }`
2. **Added fullscreen toggle button** to `ui/src/routes/notes/[id]/+page.svelte`:
   - Between Info and Download buttons in the desktop-only section
   - Shows `Minimize2` when active, `Maximize2` when not
3. **Added keyboard shortcuts**:
   - `Ctrl/Cmd+W` toggles fullscreen
   - `Escape` exits fullscreen (only when active)
4. **Exit on unmount**: `$effect(() => () => fullscreen.exit())`
5. **Hidden sidebar** when fullscreen in `ui/src/routes/+layout.svelte`:
   - Wrapped `<Sidebar />` in `{#if !fullscreen.active}`
6. **Hidden notes list pane** when fullscreen in `ui/src/routes/notes/+layout.svelte`:
   - Added `fullscreen.active ? 'hidden'` class logic

### Files Modified
- `ui/package.json` — added `katex`, `marked-katex-extension`
- `ui/src/app.css` — KaTeX CSS import + `.katex-display` styles
- `ui/src/lib/utils/markdown.ts` — KaTeX extension, DOMPurify config, preview stripping
- `ui/src/lib/stores/fullscreen.svelte.ts` — new file
- `ui/src/routes/notes/[id]/+page.svelte` — button, keyboard shortcuts, cleanup
- `ui/src/routes/+layout.svelte` — hide sidebar
- `ui/src/routes/notes/+layout.svelte` — hide notes list

### Verification
- `svelte-check`: 0 errors
- `npm run build`: success
