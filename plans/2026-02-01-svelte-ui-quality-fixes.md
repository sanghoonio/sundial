# Svelte UI Quality Fixes

## Context
Evaluation of Svelte-to-React migration concluded: stay with Svelte, fix implementation issues. After reading all critical files, the initial automated audit overstated several findings. This plan covers only the issues that are real bugs or clear quality improvements.

---

## Fix 1: Calendar sync timer race condition (BUG)
**File:** `ui/src/routes/calendar/+page.svelte`

**Problem:** The `$effect` calls `.then()` on an API fetch, and the `.then()` callback sets `syncInterval`. If the component unmounts before the promise resolves, the cleanup function fires first (clearing null), then the interval is created with nothing to ever clean it up — a memory/network leak.

**Fix:** Track the interval within the async callback's scope and use an `aborted` flag.

## Fix 2: `window.location.href` → `goto()` (BUG)
**File:** `ui/src/routes/calendar/+page.svelte`

**Problem:** `window.location.href = /tasks?project=...` causes a full page reload, losing all app state.

**Fix:** Replace with `goto()` from `$app/navigation`.

## Fix 3: Notes debounce cleanup (MINOR)
**File:** `ui/src/routes/notes/+layout.svelte`

**Problem:** `searchDebounceTimer` is never cleared on component unmount.

**Fix:** Convert to `$effect`-based debounce that auto-cleans up.

## Fix 4: Add user-facing error feedback with svelte-sonner (QUALITY)
**Scope:** Multiple pages

**Problem:** All API errors are `console.error` only. Users see loading spinners that never resolve, or silent failures with no feedback.

**Fix:** Install `svelte-sonner` and add toasts only for user-initiated action failures (not background operations).

---

## Implementation Log

### Completed

1. **Installed svelte-sonner, added `<Toaster />` to root layout**
   - Added `svelte-sonner` import and `<Toaster richColors closeButton />` after `<MobileNav />` in authenticated block

2. **Fixed calendar sync race condition**
   - Removed module-level `syncInterval` variable
   - Added `aborted` flag and local `interval` variable inside the `$effect`
   - Cleanup now correctly sets `aborted = true` and clears interval

3. **Replaced `window.location.href` with `goto()`**
   - Added `import { goto } from '$app/navigation'` to calendar page
   - Changed task click handler to use `goto()` for client-side navigation

4. **Fixed notes debounce cleanup**
   - Replaced manual `searchDebounceTimer` + `handleSearchInput` with `$effect` that returns cleanup
   - Removed redundant `oninput` handler (already handled by `bind:value`)

5. **Added error toasts to user-initiated action failures**
   - Calendar: delete event, delete series, manual sync
   - Tasks: move task, rename/delete/create/reorder column
   - Notes: wiki-link navigation failure (both "not found" and API error cases)
   - Background operations (periodic sync, initial loads) remain silent

### Build verification
- `svelte-check`: 0 new errors (1 pre-existing unrelated error in notes/new)
- `npm run build`: success
