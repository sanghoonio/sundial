# Block-Based Note Editor Implementation

## Date: 2026-01-31

## Summary
Refactored the note editor from a single textarea into a Jupyter-style block-based editor where notes are an ordered list of blocks (Markdown or Chat). Blocks can be reordered, added, and removed.

## Storage Format
Uses HTML comment delimiters (`<!-- block:md -->`, `<!-- block:chat -->`) that are invisible in standard markdown renderers. Backward compatible: notes without delimiters render as a single markdown block.

## Files Created
- `api/services/block_parser.py` -- parse_blocks, serialize_blocks, extract_markdown_text
- `ui/src/lib/utils/blocks.ts` -- gatherContext, newBlockId helpers
- `ui/src/lib/components/notes/NoteEditor.svelte` -- Block orchestrator
- `ui/src/lib/components/notes/MarkdownBlock.svelte` -- Markdown editing cell with auto-resize
- `ui/src/lib/components/notes/BlockControls.svelte` -- Move up/down/delete gutter
- `ui/src/lib/components/notes/AddBlockDivider.svelte` -- Insert point between blocks

## Files Modified
- `api/schemas/note.py` -- Added ChatMessageSchema, BlockSchema, blocks field on NoteCreate/NoteUpdate/NoteResponse
- `api/routes/notes.py` -- Parse blocks in _note_to_response, serialize in create/update, use extract_markdown_text for previews
- `api/routes/ai.py` -- Added context: str | None to ChatRequest
- `api/services/ai_service.py` -- Added context parameter to chat() method
- `ui/src/lib/types.ts` -- Added ChatMessage, MarkdownBlockData, ChatBlockData, NoteBlock types; updated Note interfaces
- `ui/src/lib/components/notes/ChatBlock.svelte` -- Refactored: messages and precedingContext are props, uses onmessageschange callback
- `ui/src/routes/notes/[id]/+page.svelte` -- Replaced textarea with NoteEditor, sends blocks on save
- `ui/src/routes/notes/new/+page.svelte` -- Replaced textarea with NoteEditor, initializes with one empty md block

## Verification
- Backend: `uv run pytest` passes (0 tests, no errors)
- Frontend: `npm run build` compiles with no errors
- Block parser: All 6 unit tests pass (plain content, empty, multi-block, round-trip, single-block optimization, markdown extraction)
- Schema validation: BlockSchema, ChatMessageSchema, NoteCreate/NoteUpdate with blocks all validated
