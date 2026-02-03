# Plan: Settings Keyboard Shortcuts & AI Provider Persistence

## Summary
1. Add Ctrl/Cmd+S keyboard shortcut to trigger save on settings pages with global save buttons
2. Investigate and fix AI provider setting reverting to "openrouter"

---

## Task 1: Keyboard Shortcut for Save

### Pages to Update
- `ui/src/routes/settings/account/+page.svelte` - calls `handleSaveUsername()`
- `ui/src/routes/settings/appearance/+page.svelte` - calls `handleSave()`
- `ui/src/routes/settings/ai/+page.svelte` - calls `handleSave()`
- `ui/src/routes/settings/calendar/+page.svelte` - calls `handleSave()`

### Existing Pattern (from `notes/new/+page.svelte:73-78`)
```typescript
function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 's') {
    e.preventDefault();
    handleCreate();
  }
}
```
```svelte
<svelte:window onkeydown={handleKeydown} />
```

### Implementation
Add to each settings page:
1. Add a `handleKeydown` function that checks for `(e.metaKey || e.ctrlKey) && e.key === 's'`
2. Call `e.preventDefault()` and trigger the save function
3. Add `<svelte:window onkeydown={handleKeydown} />` at the end of the template

---

## Task 2: AI Provider Persistence Issue

### Problem
User selects "nvidia", saves, restarts the server, and it reverts to "openrouter".

### Current Flow
- Frontend: `aiProvider = $state('openrouter')` (default), options are 'openrouter' and 'nvidia'
- Backend: `_SETTINGS_KEYS["ai_provider"] = ("str", "openrouter")` as default
- Save: `api.put('/api/settings', { ai_provider: 'nvidia' })` → writes to `UserSettings` table
- Load: `api.get('/api/settings')` → reads from `UserSettings` table, falls back to default if not found

### Investigation Findings
- Database: File-based SQLite at `./workspace/sundial.db` (persisted)
- Schema: `SettingsUpdate.ai_provider: str | None = None` (correct)
- Save logic: Iterates `updates`, creates/updates `UserSettings` record, commits

### Debugging Steps During Implementation
1. Check if `workspace/sundial.db` file exists and contains data
2. Query database directly after save: `SELECT * FROM user_settings WHERE key = 'ai_provider'`
3. Add console.log in frontend to verify load response includes correct `ai_provider`

### Possible Root Causes
- Server restart triggers database reset/migration
- Frontend showing default before `loadSettings()` completes (race condition)
- Different working directory causing different database file

### Backend Files
- `api/routes/settings.py:69-98` - update_settings endpoint
- `api/config.py:6` - DATABASE_URL configuration

---

## Files to Modify
1. `ui/src/routes/settings/account/+page.svelte`
2. `ui/src/routes/settings/appearance/+page.svelte`
3. `ui/src/routes/settings/ai/+page.svelte`
4. `ui/src/routes/settings/calendar/+page.svelte`

---

## Verification
1. Navigate to each settings page
2. Make a change to any setting
3. Press Ctrl+S (Windows/Linux) or Cmd+S (Mac)
4. Verify save indicator shows "Saved!"
5. For AI provider: select a provider, save, refresh page, confirm selection persists

---

## Implementation Log

### Completed: 2026-02-03

#### Task 1: Keyboard Shortcuts - DONE

Added `handleKeydown` function and `<svelte:window onkeydown={handleKeydown} />` to all four settings pages:

1. **account/+page.svelte** - Added keyboard handler that calls `handleSaveUsername()`
2. **appearance/+page.svelte** - Added keyboard handler that calls `handleSave()`
3. **ai/+page.svelte** - Added keyboard handler that calls `handleSave()`
4. **calendar/+page.svelte** - Added keyboard handler that calls `handleSave()`

Pattern used (consistent with notes/new/+page.svelte):
```typescript
function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 's') {
    e.preventDefault();
    handleSave(); // or handleSaveUsername() for account page
  }
}
```

#### Task 2: AI Provider Persistence - INVESTIGATION

Added console.log debugging to `ai/+page.svelte`:
- Logs `ai_provider` value when loading settings from API
- Logs `ai_provider` value when saving and after response

The backend code appears correct:
- `init_database()` uses `create_all` which doesn't reset existing tables
- Default settings are only seeded if they don't exist
- The settings PUT endpoint properly creates/updates UserSettings records

Next steps for user to verify:
1. Open browser console
2. Navigate to AI settings page
3. Check logged values match expected `ai_provider`
4. If API returns "openrouter" after saving "nvidia", the issue is backend/database
5. If API returns "nvidia" correctly, the issue may be a caching/race condition
