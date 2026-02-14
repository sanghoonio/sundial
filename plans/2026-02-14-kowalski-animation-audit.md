---
date: 2026-02-14
status: in-progress
description: Kowalski animation audit report for Sundial UI
---

# Animation Audit: Sundial

**Date**: 2026-02-14
**Stack**: SvelteKit 5 + Vite 7 + Tailwind v4 + DaisyUI v5 + svelte-sonner (toasts) + svelte-typewrite
**Project Type**: SaaS productivity app (notes, tasks, calendar, projects dashboard)
**Audited Against**: Emil Kowalski's animation & interaction design principles

---

## Summary

Sundial has a **minimal animation footprint**. The codebase relies heavily on DaisyUI's built-in behaviors for modals, dropdowns, and loading states, and uses Tailwind's `transition-colors` utility widely for hover effects. Beyond that, there are only 2 Svelte transitions, 1 CSS keyframe animation, and 2 custom CSS transitions in the entire app. The biggest strength is the swipe-to-delete gesture on NoteListItem/TaskCard (well-structured, uses `translateX`). The biggest gaps are the complete absence of `prefers-reduced-motion`, numerous conditional renders that snap in/out without animation, and no button press feedback.

### Scores

| Category | Score | Notes |
|---|---|---|
| Purpose & Frequency | pass | Minimal animation on a daily-use SaaS tool is appropriate |
| Easing | needs-work | Only built-in easings; no custom cubic-bezier curves |
| Duration & Timing | needs-work | No variation across component types; one problematic ease-in-out |
| Transform Patterns | needs-work | Good scale(0.9) on AddBlockDivider; no button :active feedback |
| Performance | needs-work | Animating max-height triggers layout thrashing |
| Interruptibility | pass | CSS transitions used for interactive states; no keyframe misuse |
| Gesture Patterns | needs-work | Swipe-to-delete uses distance-only threshold, no pointer capture |
| Micro-Interactions | fail | No button press feedback, no tooltip delay, no tab visibility handling |
| Accessibility | fail | Zero prefers-reduced-motion anywhere in the codebase |
| Motion Gaps | needs-work | Multiple dropdowns, panels, and sheets snap in/out |

---

## What's Working

- **Sidebar width transition** (`Sidebar.svelte:103`) — Uses `transition-all` on sidebar width collapse/expand. Clean GPU-friendly approach since Tailwind handles the transition property selection.

- **Swipe-to-delete with translateX** (`NoteListItem.svelte:152-153`, `TaskCard.svelte:291-292`) — Real-time swipe offset via `style:transform="translateX()"` with conditional `transition-transform duration-150` only during settling. Avoids layout thrashing, feels responsive during the drag.

- **AddBlockDivider hover animation** (`AddBlockDivider.svelte:33-34`) — `in:scale={{ start: 0.9, duration: 150 }}` and `out:fade={{ duration: 100 }}`. Correct starting scale (0.9, not 0), appropriate durations, and asymmetric enter/exit timing per Emil's principles.

- **MarkdownBlock slide transition** (`MarkdownBlock.svelte:513`) — `transition:slide={{ duration: 150 }}` for code block expand. Fast, appropriate for a frequent in-editor action.

- **Consistent hover transitions** (59 occurrences across 23 files) — `transition-colors` on nearly every interactive element provides baseline visual feedback without overdoing it.

- **Toasts via svelte-sonner** (`+layout.svelte:64`) — Sonner is built by Emil Kowalski and follows all his principles by default (transform-based animations, ~400ms timing, stacking with scale reduction).

---

## Issues

### Critical

#### No prefers-reduced-motion support
- **Location**: Entire codebase — 0 occurrences
- **Problem**: Users with vestibular motion disorders have no way to reduce or disable animations. This is a mandatory accessibility requirement.
- **Principle**: "prefers-reduced-motion media query must be respected — this is mandatory, not optional"
- **Fix**: Add a global reduced-motion rule in `app.css`:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Important

#### AI terminal animates max-height (layout property)
- **Location**: `src/routes/+page.svelte:260`
- **Problem**: `transition: max-height 0.3s ease-in-out` triggers layout recalculation on every frame. Also uses `ease-in-out` which feels sluggish for an enter/exit animation.
- **Principle**: "Never animate height/width/margin/padding" and "ease-in-out is for elements moving while remaining on screen, not enter/exit"
- **Fix**: Replace with `clip-path` reveal or fix easing. Since the element is absolutely positioned (layout impact is contained to itself), the pragmatic fix is to change the easing to `ease-out` and apply a custom curve.

#### No button press feedback
- **Location**: `src/app.css:12` and all `Button.svelte` / `btn` usages
- **Problem**: The `:active` rule only removes outlines. No scale or transform feedback on button press. Buttons feel flat and unresponsive.
- **Principle**: "Button active state: scale(0.97) — 3% reduction for tactile feedback, 150ms ease-out"
- **Fix**: Add to `app.css`:
```css
.btn:active:not(:disabled) {
  transform: scale(0.97);
  transition: transform 150ms ease-out;
}
```

#### Swipe-to-delete uses distance-only threshold
- **Location**: `NoteListItem.svelte:72`, `TaskCard.svelte:57`
- **Problem**: Snaps to revealed/hidden based on `swipeOffset < -MAX_OFFSET / 2` — a pure distance check. Quick flicks don't dismiss because velocity isn't considered.
- **Principle**: "Use velocity (not just distance) — allows quick flicks to dismiss. Threshold: 0.11"
- **Fix**: Track timestamps and calculate velocity:
```javascript
const velocity = Math.abs(swipeOffset) / (Date.now() - swipeStartTime);
if (velocity > 0.11 || swipeOffset < -MAX_OFFSET / 2) { /* dismiss */ }
```

#### No custom easing curves
- **Location**: All CSS transitions use `ease`, `ease-in-out`, or Tailwind defaults
- **Problem**: Built-in CSS easing curves are "usually not strong enough." The entire app uses generic curves with no custom `cubic-bezier()`.
- **Principle**: "Custom curves feel more energetic" — Emil recommends custom curves for any important animation
- **Fix**: Define project-level custom easings as CSS custom properties and apply to key transitions (sidebar collapse, AI terminal expand).

### Minor

#### MobileNav bottom sheet snaps in without animation
- **Location**: `MobileNav.svelte:47`
- **Problem**: `{#if moreOpen}` renders the bottom sheet instantly. No slide-up or fade.
- **Principle**: Motion gap — conditional render without animation wrapper
- **Fix**: Add `transition:fly={{ y: 200, duration: 200 }}` on the sheet div.

#### IconPicker dropdown snaps in
- **Location**: `IconPicker.svelte:30`
- **Problem**: `{#if open}` with no transition. Icon grid appears/disappears abruptly.
- **Principle**: Motion gap — dropdown without enter/exit animation
- **Fix**: Add `transition:scale={{ start: 0.95, duration: 120 }}` with `transform-origin: top left`.

#### WikiLinkSuggest dropdown has no animation
- **Location**: `WikiLinkSuggest.svelte:79`
- **Problem**: `{#if results.length > 0}` pops the suggestion list in without transition.
- **Principle**: Motion gap — visible user-facing autocomplete without animation
- **Fix**: Add `transition:fly={{ y: -4, duration: 120 }}`.

#### FlipClock doesn't flip
- **Location**: `FlipClock.svelte:33-57`
- **Problem**: The component is styled to look like a physical flip clock but digits change instantly with no animation. Missed opportunity for delight on a rare-view dashboard element.
- **Principle**: "Rare (monthly) — delightful morphing animations welcome." Dashboard is viewed daily but the clock flip is a visual signature moment.
- **Fix**: Add CSS flip animation on digit change (perspective + rotateX keyframes).

#### No tab visibility handling
- **Location**: `FlipClock.svelte:23-26`
- **Problem**: `setInterval(updateTime, 1000)` runs continuously even when tab is hidden. No `document.hidden` check.
- **Principle**: "document.hidden — pause timers when tab inactive"
- **Fix**: Add `document.addEventListener('visibilitychange', ...)` to pause/resume the interval.

#### Same duration across all transitions
- **Location**: Most explicit durations are 150ms or Tailwind defaults
- **Problem**: No duration variation by component type. A sidebar collapse, a button hover, and a code block toggle all use roughly the same timing.
- **Principle**: Duration should vary: "button feedback 150ms, general UI 200-300ms, drawers 500ms, toasts 400ms"
- **Fix**: Establish a duration scale and apply per component type.

---

## Motion Gaps

| Location | Element | Current Behavior | Suggested Animation |
|---|---|---|---|
| `MobileNav.svelte:47` | Bottom sheet menu | Snaps in/out | `transition:fly={{ y: 200, duration: 200 }}` |
| `MobileNav.svelte:41` | Backdrop overlay | Snaps in/out | `transition:fade={{ duration: 150 }}` |
| `IconPicker.svelte:30` | Icon grid dropdown | Snaps in/out | `transition:scale={{ start: 0.95, duration: 120 }}` |
| `WikiLinkSuggest.svelte:79` | Autocomplete dropdown | Snaps in/out | `transition:fly={{ y: -4, duration: 120 }}` |
| `notes/[id]/+page.svelte:632` | Find bar | Snaps in/out | `transition:fly={{ y: -8, duration: 150 }}` |
| `TaskDetailPanel.svelte:284` | Side panel | Snaps in from right | `transition:fly={{ x: 384, duration: 250 }}` |
| `TaskDetailPanel.svelte:404` | Note selector dropdown | Snaps in/out | `transition:slide={{ duration: 150 }}` |
| `notes/[id]/+page.svelte:643` | Note metadata panel | Snaps in/out | `transition:slide={{ duration: 200 }}` |
| `+layout.svelte:54-56` | Sidebar show/hide (fullscreen toggle) | Snaps in/out | `transition:fly={{ x: -224, duration: 200 }}` |

---

## Recommendations

1. **Add `prefers-reduced-motion` global rule** — 3 lines in `app.css`. Fixes the only critical accessibility issue. Effort: **low**.

2. **Add button press feedback** — Single CSS rule for `.btn:active` with `scale(0.97)`. Instantly improves tactile feel across the entire app. Effort: **low**.

3. **Fix AI terminal animation** — Replace `max-height` easing with custom curve. Fixes easing issue. Effort: **low**.

4. **Animate MobileNav bottom sheet** — Add Svelte `fly` transition. Biggest visual improvement on mobile. Effort: **low**.

5. **Add velocity-based swipe dismissal** — Track timestamps in NoteListItem/TaskCard swipe handlers. Makes quick flicks work naturally. Effort: **medium**.

6. **Define custom easing curves** — Create 2-3 project-level custom `cubic-bezier()` values as CSS custom properties. Apply to sidebar collapse, panel slides, dropdown appearances. Effort: **medium**.

7. **Close remaining motion gaps** — Add transitions to IconPicker, WikiLinkSuggest, FindBar, TaskDetailPanel, and note metadata panel. Each is ~1 line of Svelte transition directive. Effort: **medium** (cumulative).

8. **Add FlipClock animation** — CSS perspective flip on digit change. Pure delight item for the dashboard. Effort: **medium**.

9. **Add tab visibility handling** — Pause FlipClock (and any future timers) when `document.hidden`. Effort: **low**.

---

*Audited using Emil Kowalski's animation principles. Reference: emilkowal.ski, animations.dev*
