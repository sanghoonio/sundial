---
date: 2026-02-22
status: complete
description: Rewrite patch_note from line-based to string-match editing
---

# Rewrite `patch_note` to String-Match Semantics

## Context

The `patch_note` MCP tool uses line-number-based operations (`start_line`, `end_line`, `content`). This requires the LLM to count lines correctly, and when the range is off by even one line, original lines survive alongside replacement text — creating silent duplicates. The MCP response says "success" either way, so the error goes undetected.

Claude Code's own Edit tool avoids this entirely by using exact string matching (`old_string` → `new_string`). The uniqueness constraint means the match is either correct or it fails explicitly. Rewriting `patch_note` to use the same approach eliminates the class of errors structurally.

## Changes

### 1. `api/schemas/note.py` (lines 35–42)

Replace `LinePatchOperation` with `StringPatchOperation`:

```python
class StringPatchOperation(BaseModel):
    old_string: str
    new_string: str

class NotePatchContent(BaseModel):
    operations: list[StringPatchOperation]
```

### 2. `api/services/note_service.py` (lines 288–356)

Full rewrite of `patch_note_content()`. The ~70 lines of line-range math become ~30 lines of string matching:

- `old_string` cannot be empty
- `old_string` must appear exactly once in the content (0 matches → error, 2+ matches → error asking for more context)
- `new_string` replaces `old_string` (empty `new_string` = deletion)
- Multiple operations applied **sequentially** (each sees the result of the previous)
- Error messages are written for LLM consumers — they explain what went wrong and what to do

### 3. `api/mcp/server.py`

**Tool definition (lines 243–284):** New description and input schema. Key points in the description:
- Read the note first, provide exact string matches
- Uniqueness requirement + how to add context to disambiguate
- Empty `new_string` for deletion
- Sequential application for multiple operations
- Tips: include surrounding context for uniqueness, insertions via matching a nearby line

**Input schema:** `operations` array of `{ old_string, new_string }` (both required).

**`update_note` description (line ~230):** Remove "line-offset errors" phrasing, replace with "full rewrites."

**Handler `_patch_note` (lines 1110–1125):** No changes needed — it already passes `operations` as a `list[dict]` to the service, key-agnostic.

### 4. `api/routes/notes.py` — No changes

The route does `op.model_dump()` for each operation in the body. The new Pydantic model produces `{"old_string": ..., "new_string": ...}` instead of line-number fields. Everything flows through.

## Verification

Code review only — MCP testing requires deployment to the server, which the user handles manually after implementation.
