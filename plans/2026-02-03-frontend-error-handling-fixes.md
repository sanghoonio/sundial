# Frontend Code Review: Sundial UI

**Date:** 2026-02-03
**Scope:** `/ui/src/` - SvelteKit 5 + Tailwind + DaisyUI frontend

---

## Implementation Plan

### Fix 1: Silent Error Handling (17 files)

Add `toast.error()` calls alongside existing `console.error()` statements:

| File | Line | Error Message |
|------|------|---------------|
| `routes/calendar/+page.svelte` | 90 | "Failed to load calendar" |
| `routes/notes/+layout.svelte` | 62 | "Failed to load notes" |
| `routes/notes/+layout.svelte` | 149 | "Failed to import note" |
| `routes/notes/+layout.svelte` | 216 | "Failed to create journal" |
| `routes/notes/+layout.svelte` | 326 | "Failed to delete note" |
| `routes/notes/new/+page.svelte` | 47 | "Failed to create note" |
| `routes/notes/[id]/+page.svelte` | 76 | "Failed to load note" |
| `routes/notes/[id]/+page.svelte` | 155 | "Failed to delete note" |
| `routes/notes/[id]/+page.svelte` | 178 | "AI analysis failed" |
| `routes/notes/[id]/+page.svelte` | 286 | "Failed to unlink task" |
| `routes/notes/[id]/+page.svelte` | 322 | "Failed to link task" |
| `routes/tasks/[projectId]/+page.svelte` | 121 | "Failed to load projects" |
| `routes/tasks/[projectId]/+page.svelte` | 134 | "Failed to load tasks" |
| `routes/tasks/[projectId]/+page.svelte` | 174 | "Failed to move task" |
| `routes/tasks/[projectId]/+page.svelte` | 211 | "Failed to delete task" |
| `routes/tasks/[projectId]/+page.svelte` | 236 | "Failed to rename column" |
| `routes/tasks/[projectId]/+page.svelte` | 251 | "Failed to delete column" |
| `routes/tasks/[projectId]/+page.svelte` | 265 | "Failed to create column" |
| `routes/tasks/[projectId]/+page.svelte` | 285 | "Failed to reorder columns" |
| `routes/projects/+page.svelte` | 77 | "Failed to load projects" |
| `routes/projects/+page.svelte` | 125 | "Failed to load project" |
| `routes/projects/+page.svelte` | 177 | "Failed to update project" |
| `routes/projects/+page.svelte` | 210 | "Failed to delete project" |
| `routes/projects/+page.svelte` | 243 | "Failed to create project" |
| `routes/settings/ai/+page.svelte` | 42, 90 | "Failed to load/save AI settings" |
| `routes/settings/calendar/+page.svelte` | 56, 99, 121, 139 | Calendar setting errors |
| `routes/settings/data/+page.svelte` | 29, 69 | Import/export errors |
| `routes/settings/tokens/+page.svelte` | 23, 38, 52 | Token management errors |
| `routes/search/+page.svelte` | 45 | "Search failed" |
| `lib/components/tasks/TaskDetailModal.svelte` | 89, 109 | Task update/delete errors |
| `lib/components/tasks/TaskDetailPanel.svelte` | 179, 212 | Task update/delete errors |
| `lib/components/tasks/TaskCreatePanel.svelte` | 53 | "Failed to create task" |
| `lib/components/tasks/TaskCreateModal.svelte` | 71 | "Failed to create task" |
| `lib/components/tasks/TaskQuickAdd.svelte` | 31 | "Failed to create task" |
| `lib/components/dashboard/DailySuggestions.svelte` | 38 | "Failed to load suggestions" |

---

### Fix 2: Race Condition in Note Auto-Save

**File:** `ui/src/routes/notes/[id]/+page.svelte`

Clear auto-save timer when manual save is triggered:

```typescript
async function handleSave() {
    if (!title.trim()) return;
    clearTimeout(autoSaveTimer);  // ADD THIS LINE
    saving = true;
    // ... rest unchanged
}
```

---

### Fix 3: N+1 Query in TaskDetailPanel

**File:** `ui/src/lib/components/tasks/TaskDetailPanel.svelte:59-75`

Replace sequential fetches with batch fetch:

```typescript
$effect(() => {
    const idsToFetch = ids.filter(id => !fetchedNoteIds.has(id));
    if (idsToFetch.length === 0) return;

    idsToFetch.forEach(id => fetchedNoteIds.add(id));

    Promise.all(
        idsToFetch.map(id =>
            api.get<NoteResponse>(`/api/notes/${id}`)
                .then(n => ({ id, title: n.title }))
                .catch(() => ({ id, title: 'Unknown note' }))
        )
    ).then(results => {
        results.forEach(({ id, title }) => {
            linkedNoteTitles[id] = title;
        });
        linkedNoteTitles = linkedNoteTitles;
    });
});
```

---

## Files Modified

1. `ui/src/routes/notes/[id]/+page.svelte` - Race condition fix + error toasts
2. `ui/src/lib/components/tasks/TaskDetailPanel.svelte` - N+1 fix + error toasts
3. `ui/src/routes/calendar/+page.svelte` - Error toasts
4. `ui/src/routes/notes/+layout.svelte` - Error toasts
5. `ui/src/routes/notes/new/+page.svelte` - Error toasts
6. `ui/src/routes/tasks/[projectId]/+page.svelte` - Error toasts
7. `ui/src/routes/projects/+page.svelte` - Error toasts
8. `ui/src/routes/settings/ai/+page.svelte` - Error toasts
9. `ui/src/routes/settings/calendar/+page.svelte` - Error toasts
10. `ui/src/routes/settings/data/+page.svelte` - Error toasts
11. `ui/src/routes/settings/tokens/+page.svelte` - Error toasts
12. `ui/src/routes/search/+page.svelte` - Error toasts
13. `ui/src/lib/components/tasks/TaskDetailModal.svelte` - Error toasts
14. `ui/src/lib/components/tasks/TaskCreatePanel.svelte` - Error toasts
15. `ui/src/lib/components/tasks/TaskCreateModal.svelte` - Error toasts
16. `ui/src/lib/components/tasks/TaskQuickAdd.svelte` - Error toasts
17. `ui/src/lib/components/dashboard/DailySuggestions.svelte` - Error toasts

---

## Implementation Log

**Completed:** 2026-02-03

All fixes implemented successfully:

1. **Silent Error Handling** - Added `toast.error()` calls to 17 files (35+ error handlers) alongside existing `console.error()` statements. Each file that didn't already have `svelte-sonner` imported now imports `toast` from it.

2. **Race Condition Fix** - Added `clearTimeout(autoSaveTimer)` at the start of `handleSave()` in `routes/notes/[id]/+page.svelte` to prevent duplicate saves when manual save (Ctrl+S) triggers while auto-save timer is pending.

3. **N+1 Query Fix** - Refactored the linked notes fetching in `TaskDetailPanel.svelte` to batch all unfetched note IDs into a single `Promise.all()` call instead of making sequential requests in a loop.

---

## Verification

After implementation:
1. **Auto-save race condition:** Edit note, press Ctrl+S quickly - should not duplicate saves
2. **Error toasts:** Disconnect network, try operations - should see toast messages
3. **N+1 query:** Open task with multiple linked notes - should see single batch in Network tab
