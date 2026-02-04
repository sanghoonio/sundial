# Mobile UI Improvement Plan

## Summary

The Sundial app has a solid foundation for mobile (MobileNav, Tailwind breakpoints, split-pane layouts) but lacks critical touch support. This plan addresses 5 key areas to bring mobile to feature parity with desktop.

## Critical Issues

| Issue | Impact | Root Cause |
|-------|--------|------------|
| Swipe gestures don't work on touchscreens | High | Uses `wheel` events only (lines 28-56 in TaskCard.svelte) |
| Calendar event editing hidden on mobile | High | `hidden lg:flex` on sidebar (line 299 in calendar/+page.svelte) |
| TaskDetailPanel not responsive | Medium | Fixed `w-96` width (line 279 in TaskDetailPanel.svelte) |
| Kanban drag-drop doesn't work on touch | Medium | HTML5 drag API (mouse-only) |
| Inconsistent back navigation | Low | Some views missing mobile back buttons |

---

## Implementation Log

### Phase 1: Touch Swipe Support - COMPLETED

**Files modified:**
- `ui/src/lib/components/tasks/TaskCard.svelte`
- `ui/src/lib/components/notes/NoteListItem.svelte`

**Changes:**
- Added touch event handlers (`ontouchstart`, `ontouchmove`, `ontouchend`) alongside existing wheel handler
- Touch swipe uses horizontal threshold (10px) to distinguish from vertical scrolling
- Uses `e.preventDefault()` only when horizontal swipe is confirmed to preserve vertical scroll

---

### Phase 2: Calendar Mobile Event Editing - COMPLETED

**Files modified:**
- `ui/src/routes/calendar/+page.svelte`
- `ui/src/lib/components/calendar/EventModal.svelte`

**Changes:**
- Added mobile detection using `matchMedia('(max-width: 1023px)')`
- Added mobile mini-calendar toggle button with collapsible MiniCalendar
- Enhanced EventModal to match EventPanel capabilities:
  - Recurrence support via RecurrenceInput
  - Recurring instance detection and series delete
  - API calls handled internally (was previously passed data to parent)
  - Updated Props interface with `onsaved`, `ondeleted`, `onseriesdeleted` callbacks
- Mobile users now see EventModal instead of hidden desktop sidebar

---

### Phase 3: TaskDetailPanel Mobile Support - COMPLETED

**File modified:**
- `ui/src/lib/components/tasks/TaskDetailPanel.svelte`

**Changes:**
- Changed from fixed `w-96` to responsive full-screen on mobile
- Uses `fixed inset-0 z-50` on mobile, `md:relative md:w-96` on desktop
- Added mobile back button (ArrowLeft) that appears only on mobile
- Hid desktop close button (X) on mobile since back button serves same purpose

---

### Phase 4: Kanban Mobile Task Movement - COMPLETED

**File modified:**
- `ui/src/lib/components/tasks/TaskCard.svelte`

**Changes:**
- Added `milestones` and `onmove` props to Props interface
- Added mobile-only dropdown menu (MoreVertical icon) for moving tasks between milestones
- Menu shows available milestones excluding current one
- Option to remove from milestone if task has one assigned
- Hid drag grip icon on mobile (desktop-only drag-drop still works)

---

### Phase 5: Consistent Back Navigation - VERIFIED

**Files verified:**
- `ui/src/routes/settings/+layout.svelte`
- All 6 settings sub-pages

**Result:**
- All settings sub-pages already have proper mobile back buttons
- Pattern: `<a href="{base}/settings" class="btn btn-ghost btn-sm btn-square md:hidden"><ChevronLeft /></a>`
- No changes needed

---

## File Summary

| File | Phase | Change |
|------|-------|--------|
| `ui/src/lib/components/tasks/TaskCard.svelte` | 1, 4 | Touch events + move menu |
| `ui/src/lib/components/notes/NoteListItem.svelte` | 1 | Touch events |
| `ui/src/routes/calendar/+page.svelte` | 2 | Mobile modal + mini-cal toggle |
| `ui/src/lib/components/calendar/EventModal.svelte` | 2 | Add recurrence support |
| `ui/src/lib/components/tasks/TaskDetailPanel.svelte` | 3 | Full-screen on mobile |
| `ui/src/routes/settings/+layout.svelte` | 5 | Verified - no changes needed |

---

## Verification

1. **Touch swipe testing:**
   - Run `npm run dev` in `ui/`
   - Open Chrome DevTools → toggle device toolbar (mobile view)
   - Navigate to Notes → swipe left on a note item → trash button should appear
   - Navigate to Tasks board → swipe left on a task card → same behavior

2. **Calendar mobile testing:**
   - In mobile view, navigate to Calendar
   - Click on a day → event modal should open (not be hidden)
   - Toggle mini-calendar button → should show/hide

3. **TaskDetailPanel testing:**
   - Open a task from Kanban board
   - In mobile view → panel should be full-screen with back button
   - Click back → should close panel

4. **Kanban move menu testing:**
   - On mobile view, tasks show a three-dot menu
   - Clicking shows "Move to" options for available milestones

5. **Device testing:**
   - Test on actual iOS Safari and Android Chrome
   - Verify vertical scroll still works during swipe gestures
   - Confirm 44px minimum touch targets on all buttons
