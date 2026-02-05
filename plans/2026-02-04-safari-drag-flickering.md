# Fix: Safari Drag Placeholder Flickering

## Problem
Safari returns `null` for `e.relatedTarget` in `dragleave` events during HTML5 drag-and-drop. All three drag implementations used `relatedTarget` + `contains()` guards that fail in Safari, causing rapid show/hide flickering of placeholders.

## Solution
Replaced `relatedTarget` guards with drag enter/leave counters. Every `dragenter` increments, every `dragleave` decrements. State is only cleared when the counter hits 0 (truly leaving the container).

Also changed project drag threshold from 0.75 to 0.5 for symmetric feel.

## Files Modified

### `ui/src/lib/components/tasks/KanbanColumn.svelte`
- Added `dragEnterCount` counter
- Added `handleDragEnter` function (increments counter, skips column drags)
- Changed `handleDragLeave` to use counter instead of `relatedTarget`
- Reset counter in `handleDrop`
- Added `ondragenter={handleDragEnter}` to column div

### `ui/src/lib/components/tasks/KanbanBoard.svelte`
- Added `boardDragEnterCount` counter
- Added `handleBoardDragEnter` function (increments counter, only for column drags)
- Changed `handleBoardDragLeave` to use counter instead of `relatedTarget`
- Reset counter in `handleBoardDrop`
- Added `ondragenter={handleBoardDragEnter}` to board div

### `ui/src/routes/projects/+page.svelte`
- Added `gridDragEnterCount` counter
- Added `handleGridDragEnter` function (increments counter, only for project drags)
- Changed `handleGridDragLeave` to use counter instead of `relatedTarget`
- Reset counter in `handleGridDrop`
- Added `ondragenter={handleGridDragEnter}` to grid div
- Changed drag threshold from `0.75` to `0.5` for centered feel

## Implementation Log
- All changes applied cleanly
- `svelte-check`: 0 errors, 20 warnings (all pre-existing a11y warnings)
