# Phase 2a: Frontend Core Implementation

## Summary

Build the core Svelte 5 frontend with TypeScript using SvelteKit, covering auth, layout, dashboard, notes, and tasks/kanban. Defers calendar, search, settings, and projects pages to Phase 2b.

**Stack:** SvelteKit (adapter-static) + Svelte 5 (runes) + TypeScript + Tailwind CSS v4 + DaisyUI v5 + Lucide icons

---

## Status: Complete

---

## Implementation Log

### 1. Project Scaffolding - Done
- Created `ui/` with `npx sv create` (Svelte 5, TypeScript, minimal template)
- Installed: `@sveltejs/adapter-static`, `daisyui@5`, `@tailwindcss/typography`, `lucide-svelte`, `tailwindcss`, `@tailwindcss/vite`
- Configured `svelte.config.js` with adapter-static (fallback: `index.html`)
- Configured `vite.config.ts` with `@tailwindcss/vite` plugin + API proxy (`/api` -> `:8000`, `/ws` -> `ws://:8000`)
- `app.css` uses Tailwind v4 `@plugin` syntax for daisyUI and typography
- `+layout.ts` disables SSR (`ssr = false`, `prerender = false`)

### 2. API Client & Types - Done
- `src/lib/types.ts` -- Full TypeScript interfaces for all API response/request types (auth, notes, tasks, projects, calendar, dashboard, tags, search, settings, websocket)
- `src/lib/services/api.ts` -- Fetch wrapper with JWT from localStorage, JSON handling, ApiError class
- `src/lib/stores/auth.svelte.ts` -- Svelte 5 rune-based auth store (init/login/setup/logout)
- `src/lib/stores/toasts.svelte.ts` -- Toast notification store with typed messages

### 3. Auth Pages - Done
- `routes/login/+page.svelte` -- Password login, redirects to `/setup` if no password configured
- `routes/setup/+page.svelte` -- First-time password setup with confirmation
- Both use DaisyUI card layout, centered on screen

### 4. Base UI Components - Done
- `Button.svelte` -- variant/size/loading/disabled props, DaisyUI btn classes
- `Input.svelte` -- bindable value, error display, optional label
- `Card.svelte` -- hoverable, compact variants
- `Modal.svelte` -- open state, title, close handler, DaisyUI modal
- `Badge.svelte` -- variant, removable with onremove callback
- `Toast.svelte` -- Renders toast store items, fixed bottom-right

### 5. Layout & Navigation - Done
- `Sidebar.svelte` -- Collapsible sidebar with lucide icons, active state from `$page.url`
- `Header.svelte` -- Page title, user avatar dropdown with logout
- `MobileNav.svelte` -- Bottom nav bar visible below md breakpoint
- Root `+layout.svelte` -- Auth guard, loads auth on mount, redirects unauthenticated users, renders sidebar/header/content shell

### 6. Dashboard Page - Done
- `routes/+page.svelte` -- Consumes `GET /api/dashboard/today`
- Grid layout with Today's Events, Tasks Due, Recent Notes cards
- Empty states for each section
- `EventCard.svelte`, `NoteCard.svelte`, `TaskCard.svelte` (compact variant)

### 7. Notes Pages - Done
- `routes/notes/+page.svelte` -- Grid of NoteCards, debounced search, tag filter chips
- `routes/notes/new/+page.svelte` -- Title, markdown textarea, TagInput, save
- `routes/notes/[id]/+page.svelte` -- Edit title/content/tags, preview toggle, backlinks section, delete
- `TagInput.svelte` -- Autocomplete from `GET /api/tags`, add/remove badges, keyboard support

### 8. Tasks & Kanban - Done
- `routes/tasks/+page.svelte` -- Project selector dropdown, loads tasks per project
- `KanbanBoard.svelte` -- Horizontal scrolling, distributes tasks to milestone columns
- `KanbanColumn.svelte` -- Drop zone with visual feedback, task count badge
- `TaskCard.svelte` -- Draggable, priority colors, checklist progress, click to edit
- `TaskQuickAdd.svelte` -- Inline add form at bottom of each column
- `TaskDetailModal.svelte` -- Edit title/description/priority/due date/checklist, delete

### 9. WebSocket Integration - Done
- `src/lib/services/websocket.ts` -- WebSocket client with auto-reconnect (exponential backoff), message handler registry
- `src/lib/stores/websocket.svelte.ts` -- Connection state, toast on updates, refresh callback registry
- Connected in root layout when authenticated, disconnected on logout

### 10. FastAPI Static Serving - Done
- Modified `api/main.py` -- Catch-all `GET /{full_path:path}` route serves files from `ui/build/`, falls back to `index.html` for SPA routing
- Only mounted if `ui/build/` directory exists

---

## Key Decisions
- Used Tailwind CSS v4 with `@plugin` syntax (no `tailwind.config.ts` needed)
- DaisyUI v5 with light/dark theme via `--default`/`--prefersdark` flags
- HTML5 Drag and Drop API for kanban (no external library)
- Plain textarea for markdown editing (WYSIWYG deferred to Phase 3)
- Simple escaped HTML for markdown preview (proper renderer deferred)

## Build Output
- Production build: `npm run build` -> `ui/build/` (~88kB CSS gzipped to ~14kB, JS chunks well-split)
- No build errors; only benign warnings (daisyUI `@property` CSS, one intentional `autofocus`)
