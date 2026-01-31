# Phase 1 Implementation Log

## What was implemented

### Step 1: Project Scaffolding - DONE
All files created as planned. One deviation: `passlib[bcrypt]` was replaced with `bcrypt` directly due to a compatibility bug between passlib and modern bcrypt versions (passlib tries to access `bcrypt.__about__.__version__` which no longer exists).

### Step 2: Database Models - DONE
All models created as specified:
- `Note`, `Tag`, `NoteTag`, `NoteLink` in `api/models/note.py`
- `Task`, `TaskChecklist` in `api/models/task.py`
- `Project`, `ProjectMilestone` in `api/models/project.py`
- `CalendarEvent`, `NoteCalendarLink` in `api/models/calendar.py`
- `UserSettings`, `AIProcessingQueue` in `api/models/settings.py`

ID formats match spec (`note_<uuid>`, `task_<uuid>`, `proj_<name>`, `event_<uuid>`).

### Step 3: Pydantic Schemas - DONE
All schema files created. Added `EventUpdate` schema (not in original plan but needed for the PUT endpoint).

### Step 4: Authentication - DONE
- `POST /api/auth/setup` - creates initial password
- `POST /api/auth/login` - returns JWT
- `get_current_user` dependency protects all other routes
- Uses bcrypt directly instead of passlib (see Step 1 note)

### Step 5: File Service - DONE
- Markdown files written to `workspace/notes/YYYY-MM-DD/<slug>.md`
- YAML frontmatter with id, title, created, updated, tags, project_id
- Slug generation from titles
- Directory cleanup on delete

**Not implemented:**
- Chat block parsing within markdown content (mentioned in plan but not fleshed out)
- `linked_tasks` and `linked_events` fields are accepted by `write_note_file()` but never populated from the service layer

### Step 6: Core Services - DONE
- `note_service.py` - Full CRUD, dual DB+file sync, backlink queries
- `task_service.py` - Full CRUD, move between milestones, checklist management
- `link_parser.py` - Parses `[[note]]`, `[[task:id]]`, `[[event:id]]` syntax

Had to fix an async issue: SQLAlchemy async sessions can't do lazy loading, so tag assignment on notes uses explicit junction table inserts instead of `note.tags = [...]`.

### Step 7: API Routes - DONE
All endpoints created as planned:
- Notes: `GET/POST /api/notes`, `GET/PUT/DELETE /api/notes/{id}`, `GET /api/notes/{id}/backlinks`
- Tasks: `GET/POST /api/tasks`, `GET/PUT/DELETE /api/tasks/{id}`, `PUT /api/tasks/{id}/move`
- Projects: `GET/POST /api/projects`, `GET/PUT/DELETE /api/projects/{id}`, `PUT /api/projects/{id}/milestones`
- Calendar: `GET/POST/PUT/DELETE /api/calendar/events` (full CRUD, not just GET/POST as plan suggested)
- Search: `GET /api/search?q=`
- Dashboard: `GET /api/dashboard/today`

### Step 8: WebSocket + Stubs - DONE
- `websocket.py` - Connection manager with broadcast
- `ai_service.py` - Returns "AI not configured" stub
- `calendar_sync.py` - Returns "not configured" stub
- `ai.py` routes - `POST /api/ai/chat`, `POST /api/ai/analyze-note/{id}`

**Not implemented:**
- WebSocket is wired up at `/ws` but nothing in the app actually calls `manager.broadcast()` yet. No route or service triggers real-time updates.

### Step 9: Database Initialization - DONE
- Creates all tables on startup
- Creates FTS5 virtual table with triggers to keep it in sync
- Inserts default `proj_inbox` project with To Do / In Progress / Done milestones
- Creates `workspace/notes/` directory

### Step 10: Startup Integration - DONE
- All routers registered under `/api`
- Lifespan handler runs `init_database()` on startup
- CORS configured for dev origins
- WebSocket endpoint at `/ws`

**Not implemented:**
- Static file serving from `ui/build/` (no frontend exists yet, so nothing to serve)

---

## Verified working (tested via curl + Python)
- Auth setup + login returning valid JWT
- Projects list returns default Inbox with 3 milestones
- Note creation writes both DB row and markdown file with frontmatter
- Note tags stored correctly
- Wiki-link `[[...]]` parsing and backlink resolution
- FTS5 search returns matching notes
- Task creation with checklist items, assigned to first milestone
- Dashboard returns aggregated tasks + notes
- Swagger UI available at `/docs`

## Gaps / things to revisit
1. **No WebSocket events fired** - the broadcast infrastructure exists but nothing calls it
2. **No chat block parsing** - `file_service.py` doesn't parse chat-style blocks from markdown
3. **linked_tasks/linked_events not populated** in frontmatter (the parameters exist but are never passed)
4. **No static file serving** - deferred until frontend exists
5. **No migration system** - tables are created via `create_all`; no Alembic or equivalent
6. **`calendar_sync.py` is never called** from any route - it's just a standalone stub class
