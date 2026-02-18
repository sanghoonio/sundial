---
date: 2026-02-17
status: complete
description: Fix three frontend issues - mobile navbar overlap, fullscreen navbar, project drag-and-drop
---

## Context

Three frontend bugs on mobile/narrow viewports:
1. Bottom navbar overlaps note content (can't see/reach bottom of notes)
2. Fullscreen mode doesn't hide the mobile navbar
3. Project drag-and-drop only works on first row when cards wrap

## Fix 1: Mobile navbar blocks bottom of note content

**Root cause:** The notes layout uses `absolute inset-0` (`notes/+layout.svelte:449`) which fills the entire padding box of `<main>`, bypassing the `pb-20` that the root layout applies for mobile navbar clearance. The scrollable content areas inside have no bottom padding to compensate.

**Changes:**

- **`ui/src/routes/notes/[id]/+page.svelte` line 644** — Note editor scroll container:
  Change `p-4 md:p-6` → `p-4 pb-20 md:p-6`
  (Mobile gets 5rem bottom padding to clear the dock; `md:p-6` overrides all sides on desktop)

- **`ui/src/routes/notes/+layout.svelte` line 656** — Notes list scroll container:
  Add `pb-20 md:pb-0` to existing classes
  (The notes list is visible on mobile when no note is selected)

## Fix 2: Fullscreen hides mobile navbar

**Root cause:** `MobileNav` is rendered unconditionally in `+layout.svelte:63`. The fullscreen store already hides the sidebar but doesn't affect MobileNav. The fullscreen toggle button is also desktop-only (`hidden md:flex`).

**Changes:**

- **`ui/src/routes/+layout.svelte` line 63** — Wrap MobileNav in conditional:
  `{#if !fullscreen.active}<MobileNav />{/if}`
  (fullscreen store is already imported at line 8)

- **`ui/src/routes/notes/[id]/+page.svelte` line 557** — Fullscreen toggle button:
  Change `hidden md:flex` → `flex`
  (Makes the button visible on mobile so users can actually enter/exit fullscreen)

## Fix 3: Project drag-and-drop on narrow viewports

**Root cause:** `handleGridDragOver()` (`projects/+page.svelte:367-393`) only checks `e.clientX` to determine drop position. On mobile with `grid-cols-2`, cards wrap to multiple rows with overlapping X ranges. The X-only check matches first-row cards regardless of cursor Y position.

**Change in `ui/src/routes/projects/+page.svelte`** — Replace `handleGridDragOver()` (lines 367-393) with row-aware algorithm:

1. Group non-dragged cards into rows by comparing `rect.top` values (tolerance: half card height)
2. Find which row the cursor is in using Y coordinate
3. Within that row, find insertion point using 50% X threshold (left half → insert before, right half → insert after)
4. Fallbacks: cursor below all rows → append at end; cursor above → insert at beginning; between rows → snap to closest row

## Files to modify

| File | What |
|------|------|
| `ui/src/routes/notes/[id]/+page.svelte` | Add `pb-20` to scroll container (L644), show fullscreen button on mobile (L557) |
| `ui/src/routes/notes/+layout.svelte` | Add `pb-20 md:pb-0` to notes list (L656) |
| `ui/src/routes/+layout.svelte` | Conditionally render MobileNav (L63) |
| `ui/src/routes/projects/+page.svelte` | Rewrite `handleGridDragOver()` (L367-393) |

## Verification

- Mobile notes: open a long note, scroll to the bottom — content should be fully visible above the navbar
- Notes list: with no note selected on mobile, scroll notes list to bottom — last item should be fully visible
- Fullscreen: on mobile, tap fullscreen button in note editor — navbar should disappear; tap again — navbar returns
- Project drag-and-drop: on narrow viewport (or mobile), with 4+ projects wrapping to 2 rows, drag a project from row 2 to row 1 and vice versa — drop indicator should appear at correct position
