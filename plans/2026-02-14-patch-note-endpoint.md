---
date: 2026-02-14
status: complete
description: Add patch_note API and MCP endpoint for line-based edits to note content
---

# Patch Note Endpoint

## Context

The current `update_note` MCP tool requires sending the entire note content to change even a single word. For AI agents making small edits to long notes, this is wasteful and error-prone. This plan adds a `patch_note` capability that accepts line-number-based operations — the AI reads the note (sees line numbers), identifies what to change, then sends precise line-range updates.

## Approach

Operations specify `{start_line, end_line, content}` to replace a range of lines with new content. The service splits the note content by newlines, validates line numbers, applies operations from bottom-to-top (so line numbers remain stable across multiple operations), and delegates to the existing `update_note()` for all downstream effects.

### Operation semantics

- **Replace lines**: `{start_line: 5, end_line: 7, content: "new line 5\nnew line 6"}` — replaces lines 5-7 with new content (can be fewer or more lines)
- **Delete lines**: `{start_line: 5, end_line: 7, content: ""}` — removes lines 5-7
- **Insert after line**: `{start_line: 6, end_line: 5, content: "inserted line"}` — when start > end, inserts after line `end` (i.e. start_line=6, end_line=5 means "insert before line 6")

Lines are 1-indexed to match what the AI sees when reading note content.

Operations are sorted and applied bottom-to-top internally so that multiple operations don't shift each other's line numbers.

## Changes

### 1. Schema — `api/schemas/note.py`

Add after `NoteUpdate` (line 32):

```python
class LinePatchOperation(BaseModel):
    start_line: int
    end_line: int
    content: str

class NotePatchContent(BaseModel):
    operations: list[LinePatchOperation]
```

### 2. Service — `api/services/note_service.py`

Add `patch_note_content()` after the existing `update_note()` function:

- Takes `note_id` and `operations: list[dict]`
- Fetches note via existing `get_note()`
- Splits `note.content` into lines
- Validates all line numbers are in range (1 to len(lines))
- Validates operations don't overlap
- Sorts operations by `start_line` descending (bottom-to-top application)
- For each operation: replaces `lines[start-1:end]` with `content.splitlines()` (or removes lines if content is empty)
- Joins lines back and delegates to existing `update_note(db, note_id, content=patched_content)`
- Raises `ValueError` with clear message if line numbers are out of range or operations overlap

### 3. REST endpoint — `api/routes/notes.py`

Add after the `update_note` PUT route (line 98):

- `PATCH /{note_id}/content` with `NotePatchContent` body
- Catches `ValueError` → HTTP 422
- Note not found → HTTP 404
- Same post-update behavior: WebSocket broadcast + background AI processing

### 4. MCP tool — `api/mcp/server.py`

Three additions:
- **Tool definition** in `_tool_list()` after `update_note` (line 242): `patch_note` with `note_id` + `operations` array schema (each op has `start_line`, `end_line`, `content`)
- **Dispatch** in `handle_call_tool()` after line 377: `elif name == "patch_note"`
- **Handler** `_patch_note()` after `_update_note` (line 1063): validates inputs, calls `patch_note_content`, catches `ValueError`, broadcasts WebSocket event
- **Import** on line 24: add `patch_note_content` to the existing note_service import

## Error handling

| Scenario | MCP | REST |
|---|---|---|
| Note not found | Text error | 404 |
| Line number out of range | Text error with details | 422 |
| Overlapping operations | Text error | 422 |

## Verification

1. Deploy to server
2. Test via MCP: call `patch_note` with a note ID and an operation like `{start_line: 3, end_line: 3, content: "updated line"}`
3. Confirm content changed with `get_note`
4. Test multi-operation: two non-overlapping line edits in one call
5. Test error case: out-of-range line number, confirm error message
6. Test via REST: `PATCH /api/notes/{id}/content` with same payload
