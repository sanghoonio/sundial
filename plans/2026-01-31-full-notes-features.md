# Full Notes Features Implementation

## Summary

Upgraded the notes system from a basic textarea/escaped-HTML implementation to a full-featured markdown editing experience with AI integration, wiki-links, project assignment, and improved list management.

**Stack:** marked + DOMPurify for markdown, Svelte 5 runes, DaisyUI v5, Lucide icons

---

## Status: Complete

---

## Implementation Log

### 1. Dependencies - Done
- Installed `marked` (markdown parser), `dompurify` + `@types/dompurify` (HTML sanitization)

### 2. Markdown Rendering Utility (`lib/utils/markdown.ts`) - Done
- `renderMarkdown(content)` -- Parses markdown to sanitized HTML via marked + DOMPurify
- Custom `wikiLink` extension for marked that handles `[[note-title]]`, `[[task:id]]`, `[[event:id]]` syntax
  - Wiki-links render as `<a>` tags with `wiki-link` CSS class and `data-title`/`data-type`/`data-id` attributes
- `markdownPreview(content, maxLength)` -- Strips markdown syntax to produce plain-text preview
  - Handles headings, bold, italic, code, links, wiki-links, images, lists, blockquotes, horizontal rules

### 3. Markdown Toolbar (`lib/components/notes/MarkdownToolbar.svelte`) - Done
- Operates on a bound `<textarea>` element via selection API
- Buttons: Bold, Italic, Inline Code | Heading, Bullet List, Numbered List, Blockquote | Link, Wiki Link `[[...]]`, Horizontal Rule
- `wrap(before, after)` -- Wraps selected text (or inserts placeholder)
- `insertAtLineStart(prefix)` -- Toggles line-start prefix (for headings, lists, quotes)
- `insertText(text)` -- Inserts text at cursor
- All operations dispatch `input` events to keep Svelte bindings in sync
- Uses Lucide icons, DaisyUI btn-ghost btn-xs styling

### 4. AI ChatBlock (`lib/components/notes/ChatBlock.svelte`) - Done
- Embeddable AI chat panel for notes
- DaisyUI chat bubbles (user = chat-end primary, assistant = chat-start)
- Sends messages to `POST /api/ai/chat` with `note_id` context
- Loading state with animated dots
- Collapsible (minimize/maximize toggle)
- Removable via onremove callback
- Auto-scrolls to latest message

### 5. Project Selector (`lib/components/notes/ProjectSelect.svelte`) - Done
- Reusable dropdown that loads projects from `GET /api/projects`
- Bindable `value` (string | null)
- "No project" default option

### 6. Note Edit Page (`routes/notes/[id]/+page.svelte`) - Rewritten
- **Markdown toolbar** above textarea (hidden in preview mode)
- **Real markdown preview** via `renderMarkdown()` with prose styling
- **Project selector** alongside tag input
- **AI Analyze button** (sparkle icon) -- calls `POST /api/ai/analyze-note/{id}`, applies suggested tags, shows toast for extracted tasks
- **AI Chat toggle** (message icon) -- shows/hides ChatBlock below editor
- **Keyboard shortcut** -- Cmd/Ctrl+S saves note, hint shown next to Save button
- Tags, project, backlinks, linked items all retained from Phase 2a

### 7. New Note Page (`routes/notes/new/+page.svelte`) - Rewritten
- Same markdown toolbar + real preview as edit page
- Project selector alongside tag input
- Cmd/Ctrl+S keyboard shortcut
- Preview toggle in top bar

### 8. NoteCard (`lib/components/notes/NoteCard.svelte`) - Enhanced
- Uses `markdownPreview()` for clean plain-text previews (strips markdown syntax)
- Shows project indicator icon (FolderKanban) when note has a project
- Shows linked task count and linked event count with icons
- Shows "+N" overflow indicator when more than 3 tags

### 9. Notes List Page (`routes/notes/+page.svelte`) - Enhanced
- **Sort dropdown** -- Newest first (default), Oldest first, Title A-Z, Title Z-A (client-side sort)
- **Pagination** -- Loads 30 notes at a time with "Load more (N of total)" button
- **Client-side filter** -- Filters by title, preview text, and tags (backend notes API doesn't have search param)
- **Tag filter chips** -- Unchanged from Phase 2a
- Debounced search input (200ms)

---

## Key Decisions
- Used `marked` with a custom tokenizer extension for wiki-links rather than regex post-processing
- DOMPurify sanitization with `ADD_ATTR` for custom data attributes on wiki-links
- Markdown toolbar operates on textarea via `setRangeText()` API rather than contenteditable
- Client-side sort/filter since backend `GET /notes` only supports tag and project_id filtering
- ChatBlock is a toggle panel rather than a persistent block-based system (simpler for MVP)
- AI analyze merges suggested tags into existing tags immediately, shows toast for discovered tasks

## Build Output
- Production build succeeds with no errors
- New chunk: `marked` + `dompurify` bundle (~65kB gzipped ~22kB)
