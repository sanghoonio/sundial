# Sundial

A self-hosted personal productivity workspace. Works fully offline with optional AI enhancements.

## Features

- **Notes** — Block-based editor mixing markdown and AI chat blocks. Wiki-style `[[linking]]` between notes, tasks, and events. Rich rendering: LaTeX math, syntax-highlighted code, Mermaid diagrams. Full-text search (FTS5). Auto-save. Find-in-note with match highlighting. Export to markdown. Notes stored as portable `.md` files with YAML frontmatter.

- **Tasks** — Kanban board organized by project milestones. Drag-and-drop between columns. Checklists/subtasks. Priority levels and due dates. Tasks appear on the calendar alongside events. AI can suggest tasks extracted from notes.

- **Calendar** — Month, week, day, and agenda views. CalDAV sync (Google Calendar, Outlook, Nextcloud, etc.) with recurring event support (RRULE). Create local events. Tasks with due dates shown inline. Event linking to notes.

- **Projects** — Group notes and tasks under projects. Custom milestone columns for each project's kanban board. Color and icon customization.

- **Search** — Full-text search across notes and tasks with FTS5. Debounced results with content snippets and highlighted matches.

- **Dashboard** — Today's events, due tasks, and recent notes at a glance. AI daily suggestions with prioritized action items (typewriter-animated terminal display).

- **AI Integration (Optional)** — Background auto-tagging, task extraction from note content, calendar event linking. In-note chat blocks for AI conversations with context. Daily planning suggestions. Supports OpenRouter and NVIDIA providers. All features work without AI enabled.

- **MCP Server** — Expose notes, tasks, calendar, and projects to external AI tools (e.g., Claude Desktop) via the Model Context Protocol over SSE. Token-authenticated.

## Architecture

### Data Storage

Sundial uses a **hybrid storage model** — everything lives in the `workspace/` directory for easy backup and portability.

**Filesystem — Note content as markdown files:**

- Notes are written as `.md` files at `workspace/notes/YYYY-MM-DD/slugified-title.md`
- Each file has YAML frontmatter (id, title, created, updated, tags, project, linked tasks/events)
- Content is plain markdown — readable and editable outside Sundial
- Filename collisions handled with `-N` suffixes
- Files are written on every create/update and deleted on note deletion

**SQLite — Metadata, relationships, and indexes:**

- `workspace/sundial.db` holds all structured data
- **Notes table** — title, filepath pointer, content (full markdown duplicated from the file for querying), project assignment, timestamps, archive flag
- Note content lives in both places: the `.md` file exists so you can browse, export, or back up notes as plain readable files without needing SQL queries. The SQLite `content` column is the working copy used for fast API reads and FTS5 search
- **Tags / note_tags** — many-to-many tagging with an `ai_suggested` flag to distinguish human vs AI tags
- **Tasks / task_checklists** — title, description, status (in_progress/done), priority (low/medium/high/urgent), due date, position for kanban ordering, subtask checklists
- **Projects / project_milestones** — project metadata (name, color, icon, status) plus ordered milestone columns that form the kanban board
- **Calendar events** — local and synced events with full RRULE recurrence support, CalDAV sync metadata (etag, href, external_id), and recurrence exception tracking
- **Junction tables** — `task_notes`, `note_calendar_links`, `note_links` (wiki-link graph) connecting items across types
- **Full-text search** — FTS5 virtual table (`notes_fts`) with columns for id, title, content, and tags. Manually synced on every note create/update/delete (not auto-triggered). Search queries are tokenized and converted to prefix-match format (`word*`) for instant-feeling results. The FTS index reads from the SQLite `content` column, not the filesystem
- **Settings** — key-value store for user preferences, AI config, calendar sync config
- **Auth tokens** — hashed tokens with type (session/api_key), scope (read/read_write), and usage tracking
- **AI processing queue** — tracks background AI jobs (pending/processing/completed/failed)
- All IDs use readable prefixes: `note_`, `task_`, `proj_`, `event_` + 12-char hex

### API

FastAPI backend at `/api/*` with JWT auth. REST endpoints for notes, tasks, projects, calendar, search, dashboard, AI, settings, and tags. WebSocket at `/ws` pushes real-time updates (AI processing results, data changes) to connected clients.

### MCP Server

Model Context Protocol server at `/mcp` over SSE. Exposes 21 tools for notes, tasks, calendar, projects, tags, dashboard, and cross-entity linking. Bearer token auth via API keys. Lets external AI assistants (e.g., Claude Desktop, Claude Code) read and write Sundial data directly.

### Frontend

SvelteKit SPA with Svelte 5 runes for reactive state. Consumes the REST API with an authenticated HTTP client. WebSocket connection for live toast notifications on AI events. Served as a static build from FastAPI in production, or as a Vite dev server during development.

## Tech Stack

| Layer    | Technology                     |
|----------|--------------------------------|
| Backend  | Python, FastAPI, SQLAlchemy    |
| Database | SQLite                         |
| Frontend | SvelteKit, Tailwind, DaisyUI   |

## Quick Start

```bash
# Clone and enter directory
git clone <repo-url> sundial
cd sundial

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings (see Configuration below)

# Backend setup
python -m venv .venv
source .venv/bin/activate
uv sync
uvicorn api.main:app --reload

# Frontend setup (new terminal)
cd ui
npm install
npm run dev
```

Visit `http://localhost:5173` (or your configured base path).

## Configuration

Environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (required) | — |
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:///./workspace/sundial.db` |
| `WORKSPACE_DIR` | Markdown files directory | `./workspace` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:5173,http://localhost:3000` |
| `BASE_PATH` | Subpath for deployment (e.g., `/sundial`) | empty (root) |

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Development vs Production

**Development** runs two servers:
- Backend: `uvicorn api.main:app --reload` (port 8000)
- Frontend: `npm run dev` (port 5173)

**Production** builds the frontend and serves everything from FastAPI:

```bash
cd ui
PUBLIC_BASE_PATH=/sundial npm run build  # if using base path
# or just: npm run build

# The built files are served automatically by FastAPI
cd ..
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Deployment Notes

### Reverse Proxy

When running behind nginx or similar:

```nginx
location /sundial/ {
    proxy_pass http://localhost:8000/sundial/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Ensure `BASE_PATH` in `.env` matches your proxy path.

### HTTPS

For remote access, terminate TLS at your reverse proxy. Sundial itself serves HTTP.

### CORS

Update `CORS_ORIGINS` to include your production domain:

```
CORS_ORIGINS=https://yourdomain.com
```

### Backups

Sundial stores all data in two locations:

- `workspace/sundial.db` — SQLite database (tasks, settings, calendar cache)
- `workspace/` — Markdown note files

Back up the entire `workspace/` directory to preserve all data.

## License

MIT
