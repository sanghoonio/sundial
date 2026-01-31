# Sundial - Phase 1: Backend + Database Implementation Plan

## Overview
Set up the FastAPI backend, SQLite database, hybrid file storage, and core CRUD APIs for notes, tasks, and projects. AI and calendar sync will be stubbed.

---

## Step 1: Project Scaffolding

**Files to create:**
- `api/main.py` - FastAPI app entry point, CORS, lifespan, static file serving
- `api/config.py` - Pydantic Settings class loading from `.env`
- `api/database.py` - SQLAlchemy async engine, session factory, Base
- `.env.example` - Template for environment variables
- `requirements.txt` - Python dependencies
- `.gitignore` - Python/Node ignores

**Dependencies:** FastAPI, uvicorn, SQLAlchemy, aiosqlite, python-jose, bcrypt, python-multipart, pydantic-settings, python-frontmatter, PyYAML

---

## Step 2: Database Models

**Files to create:**
- `api/models/__init__.py`
- `api/models/note.py` - `Note`, `Tag`, `NoteTag`, `NoteLink` models
- `api/models/task.py` - `Task`, `TaskChecklist` models
- `api/models/project.py` - `Project`, `ProjectMilestone` models
- `api/models/calendar.py` - `CalendarEvent`, `NoteCalendarLink` models
- `api/models/settings.py` - `UserSettings`, `AIProcessingQueue` models

**Key details:**
- IDs: `note_<uuid>`, `task_<uuid>`, `proj_<name>`, `event_<uuid>`
- Notes have `filepath` (unique), linked to tags via junction table
- Tasks belong to projects, have `milestone_id` for kanban column
- Projects have ordered milestones (kanban columns)
- Default project: `proj_inbox` with To Do / In Progress / Done
- FTS5 virtual table for full-text search on note content

---

## Step 3: Pydantic Schemas

**Files to create:**
- `api/schemas/__init__.py`
- `api/schemas/note.py` - NoteCreate, NoteUpdate, NoteResponse, NoteList
- `api/schemas/task.py` - TaskCreate, TaskUpdate, TaskMove, TaskResponse
- `api/schemas/project.py` - ProjectCreate, ProjectUpdate, MilestoneUpdate, ProjectResponse
- `api/schemas/calendar.py` - EventCreate, EventResponse
- `api/schemas/auth.py` - LoginRequest, TokenResponse
- `api/schemas/search.py` - SearchQuery, SearchResult

---

## Step 4: Authentication

**Files to create:**
- `api/utils/auth.py` - JWT token creation/verification, password hashing, `get_current_user` dependency
- `api/routes/auth.py` - `POST /api/auth/login`, `POST /api/auth/setup` (initial password)

**Details:**
- Single-user auth with bcrypt password hash stored in `user_settings`
- JWT tokens with 24-hour expiration
- Protected routes use `Depends(get_current_user)`

---

## Step 5: File Service (Markdown + YAML Frontmatter)

**Files to create:**
- `api/services/file_service.py`

**Responsibilities:**
- Create/read/update/delete markdown files in `workspace/notes/YYYY-MM-DD/`
- Parse and write YAML frontmatter (id, title, created, updated, tags, linked_tasks, linked_events, project_id)
- Generate slug-based filenames from note titles
- Handle date-organized directory structure
- Parse chat blocks within markdown content

---

## Step 6: Core Services

**Files to create:**
- `api/services/__init__.py`
- `api/services/note_service.py` - CRUD operations, sync between DB and files, backlink queries
- `api/services/task_service.py` - CRUD, move between milestones, checklist management
- `api/services/link_parser.py` - Parse `[[note]]`, `[[task:id]]`, `[[event:id]]` wiki-links

**Key logic:**
- Notes: Create writes both DB row and markdown file; update syncs both; delete removes both
- Tasks: Create assigns to project milestone; move updates milestone_id + position
- Link parser: Extract references from markdown content, update `note_links` table

---

## Step 7: API Routes

**Files to create:**
- `api/routes/__init__.py`
- `api/routes/notes.py` - `GET/POST /api/notes`, `GET/PUT/DELETE /api/notes/{id}`, `GET /api/notes/{id}/backlinks`
- `api/routes/tasks.py` - `GET/POST /api/tasks`, `GET/PUT/DELETE /api/tasks/{id}`, `PUT /api/tasks/{id}/move`
- `api/routes/projects.py` - `GET/POST /api/projects`, `GET/PUT/DELETE /api/projects/{id}`, `PUT /api/projects/{id}/milestones`
- `api/routes/calendar.py` - `GET/POST /api/calendar/events` (basic CRUD, sync stubbed)
- `api/routes/search.py` - `GET /api/search` using FTS5
- `api/routes/dashboard.py` - `GET /api/dashboard/today` (today's tasks, events, recent notes)

---

## Step 8: WebSocket + Stubs

**Files to create:**
- `api/utils/websocket.py` - WebSocket connection manager (broadcast to connected clients)
- `api/services/ai_service.py` - Stub returning "AI not configured" when no API key
- `api/services/calendar_sync.py` - Stub for Google/Outlook sync
- `api/routes/ai.py` - `POST /api/ai/chat`, `POST /api/ai/analyze-note/{id}` (stubbed)

---

## Step 9: Database Initialization + Migrations

**Files to create:**
- `api/init_db.py` - Create tables, insert default project (proj_inbox), create FTS5 table, set up workspace directories

---

## Step 10: Startup Integration + Dev Server

**Updates to:** `api/main.py`

- Register all route modules under `/api`
- Add lifespan handler to run DB init on startup
- Serve static files from `ui/build/` at root (for future frontend)
- Add CORS middleware for dev (localhost:5173)
- Uvicorn runner with `--reload` for development

---

## Deferred to Later Phases
- Frontend (Phase 2)
- AI integration - real Claude API calls (Phase 4)
- Calendar sync - real Google/Outlook API calls (Phase 4)
- Background task scheduler (APScheduler)
- HTTPS / production deployment

---

## Verification Plan
1. Run `uvicorn api.main:app --reload` - server starts without errors
2. Test auth: `POST /api/auth/setup` to create password, `POST /api/auth/login` to get JWT
3. Test notes CRUD: Create a note, verify markdown file appears in `workspace/notes/`, read it back, update it, delete it
4. Test tasks: Create a project, add tasks, move tasks between milestones
5. Test search: Create notes with content, verify FTS5 search returns results
6. Test dashboard: Verify `/api/dashboard/today` returns aggregated data
7. Verify backlinks: Create notes with `[[wiki-links]]`, check backlinks endpoint
8. Interactive API docs available at `/docs` (Swagger UI)
