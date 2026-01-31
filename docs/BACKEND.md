# Backend Specification

## Architecture

### Application Deployment
FastAPI serves both the API and the compiled Svelte frontend:
```python
# api/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# API routes first (they take precedence)
app.include_router(notes_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
# ... other API routes

# Serve compiled UI at root (must be last)
app.mount("/", StaticFiles(directory="../ui/build", html=True), name="ui")
```

**Request routing:**
- `/api/*` → FastAPI routes
- `/*` → Svelte SPA (serves index.html for client-side routing)

**Build process:**
1. `cd ui && npm run build` (outputs to `ui/build/`)
2. FastAPI serves `ui/build/` at root
3. Single server, single port

### FastAPI Application Structure
```
api/
├── main.py                    # Application entry point, CORS, middleware, static file serving
├── config.py                  # Configuration, environment variables
├── database.py                # SQLAlchemy setup, session management
├── models/
│   ├── __init__.py
│   ├── note.py               # SQLAlchemy models
│   ├── task.py
│   ├── project.py
│   └── calendar.py
├── schemas/
│   ├── __init__.py
│   ├── note.py               # Pydantic schemas for API
│   ├── task.py
│   ├── project.py
│   └── calendar.py
├── routes/
│   ├── __init__.py
│   ├── notes.py              # Note CRUD endpoints
│   ├── tasks.py              # Task/Kanban endpoints
│   ├── projects.py           # Project management
│   ├── calendar.py           # Calendar sync
│   ├── search.py             # Search/filter endpoints
│   └── ai.py                 # AI features (when enabled)
├── services/
│   ├── __init__.py
│   ├── note_service.py       # Business logic for notes
│   ├── task_service.py
│   ├── calendar_sync.py      # Google/Outlook integration
│   ├── ai_service.py         # Claude API wrapper
│   ├── file_service.py       # Markdown file operations
│   └── link_parser.py        # Parse [[links]] from content
├── utils/
│   ├── __init__.py
│   ├── auth.py               # JWT authentication
│   ├── websocket.py          # WebSocket manager
│   └── background.py         # Background task runner
├── migrations/
│   └── 001_initial_schema.sql
└── tests/
    ├── test_notes.py
    ├── test_tasks.py
    └── fixtures/
```

## API Endpoints

### Authentication

#### POST /api/auth/login
```json
Request:
{
  "username": "admin",
  "password": "secure_password"
}

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### GET /api/auth/me
Headers: `Authorization: Bearer {token}`
```json
Response:
{
  "username": "admin",
  "settings": {
    "ai_enabled": false,
    "calendar_source": "google"
  }
}
```

### Notes

#### GET /api/notes
Query parameters:
- `search`: Full-text search query
- `tags`: Comma-separated tag names
- `project_id`: Filter by project
- `date_from`, `date_to`: Date range
- `limit`, `offset`: Pagination

```json
Response:
{
  "notes": [
    {
      "id": "note_abc123",
      "title": "Meeting with Design Team",
      "filepath": "notes/2025-01-30/meeting-with-design-team.md",
      "created_at": "2025-01-30T14:30:00Z",
      "updated_at": "2025-01-30T16:45:00Z",
      "tags": ["design", "meetings"],
      "project_id": "proj_design_system",
      "linked_tasks": ["task_789"],
      "linked_events": ["event_456"],
      "preview": "Discussed the new component library..." // First 200 chars
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

#### POST /api/notes
```json
Request:
{
  "title": "New Note",
  "content": "# Heading\n\nContent here...",
  "tags": ["design"],
  "project_id": "proj_inbox"
}

Response:
{
  "id": "note_xyz789",
  "title": "New Note",
  "filepath": "notes/2025-01-30/new-note.md",
  "created_at": "2025-01-30T20:00:00Z",
  "updated_at": "2025-01-30T20:00:00Z",
  "tags": ["design"],
  "project_id": "proj_inbox"
}

// If AI enabled, background task queued:
// - Extract additional tags
// - Parse links [[note]], [[task:id]]
// - Detect calendar event mentions
// - Suggest tasks
// WebSocket notification sent when complete
```

#### GET /api/notes/{note_id}
```json
Response:
{
  "id": "note_abc123",
  "title": "Meeting with Design Team",
  "content": "# Meeting Notes\n\nDiscussed...",  // Full markdown content
  "filepath": "notes/2025-01-30/meeting-with-design-team.md",
  "created_at": "2025-01-30T14:30:00Z",
  "updated_at": "2025-01-30T16:45:00Z",
  "tags": ["design", "meetings"],
  "project_id": "proj_design_system",
  "linked_notes": ["note_xyz"],      // Backlinks
  "linked_tasks": ["task_789"],
  "linked_events": ["event_456"]
}
```

#### PUT /api/notes/{note_id}
```json
Request:
{
  "title": "Updated Title",
  "content": "Updated content...",
  "tags": ["design", "architecture"]
}

Response: Same as POST /api/notes
```

#### DELETE /api/notes/{note_id}
```json
Response:
{
  "success": true,
  "deleted_id": "note_abc123"
}
```

#### GET /api/notes/{note_id}/backlinks
```json
Response:
{
  "notes": [
    {
      "id": "note_xyz",
      "title": "Follow-up from meeting",
      "created_at": "2025-01-31T10:00:00Z"
    }
  ],
  "tasks": [
    {
      "id": "task_789",
      "title": "Review Figma designs",
      "status": "todo"
    }
  ]
}
```

### Tasks

#### GET /api/tasks
Query parameters:
- `project_id`: Filter by project
- `status`: Filter by status/milestone
- `due_date`: Filter by due date
- `ai_suggested`: true/false

```json
Response:
{
  "tasks": [
    {
      "id": "task_789",
      "title": "Review Figma designs",
      "description": "Check the component library mockups",
      "status": "todo",
      "priority": 1,
      "due_date": "2025-02-02",
      "project_id": "proj_design_system",
      "milestone_id": 1,
      "source_note_id": "note_abc123",
      "calendar_event_id": null,
      "ai_suggested": false,
      "created_at": "2025-01-30T14:30:00Z",
      "checklist": [
        {"id": 1, "text": "Review header components", "completed": false},
        {"id": 2, "text": "Check button variants", "completed": true}
      ]
    }
  ]
}
```

#### POST /api/tasks
```json
Request:
{
  "title": "New Task",
  "description": "Task details",
  "project_id": "proj_inbox",
  "status": "todo",
  "priority": 0,
  "due_date": "2025-02-05",
  "source_note_id": "note_abc123"
}

Response: Task object
```

#### PUT /api/tasks/{task_id}
```json
Request:
{
  "status": "in_progress",
  "priority": 2
}

Response: Updated task object
```

#### PUT /api/tasks/{task_id}/move
```json
Request:
{
  "milestone_id": 2  // Move to different column
}

Response: Updated task object
```

#### POST /api/tasks/{task_id}/checklist
```json
Request:
{
  "items": [
    {"text": "Subtask 1", "completed": false},
    {"text": "Subtask 2", "completed": false}
  ]
}

Response: Updated task with checklist
```

#### POST /api/tasks/{task_id}/accept
Accept an AI-suggested task (removes ai_suggested flag)
```json
Response: Updated task
```

#### DELETE /api/tasks/{task_id}
```json
Response: {"success": true}
```

### Projects

#### GET /api/projects
```json
Response:
{
  "projects": [
    {
      "id": "proj_design_system",
      "title": "Design System",
      "description": "Build component library",
      "status": "active",
      "created_at": "2025-01-15T10:00:00Z",
      "milestones": [
        {"id": 1, "title": "Research", "position": 0},
        {"id": 2, "title": "Prototype", "position": 1},
        {"id": 3, "title": "Done", "position": 2}
      ],
      "task_count": 12
    }
  ]
}
```

#### POST /api/projects
```json
Request:
{
  "title": "New Project",
  "description": "Project description",
  "milestones": ["To Do", "In Progress", "Done"]  // Optional, defaults to standard
}

Response: Project object
```

#### PUT /api/projects/{project_id}
```json
Request:
{
  "title": "Updated Title",
  "status": "completed"
}

Response: Updated project
```

#### PUT /api/projects/{project_id}/milestones
```json
Request:
{
  "milestones": [
    {"id": 1, "title": "Research", "position": 0},
    {"title": "New Milestone", "position": 3}  // No ID = create new
  ]
}

Response: Updated project with milestones
```

### Calendar

#### GET /api/calendar/events
Query parameters:
- `start_date`: ISO date
- `end_date`: ISO date

```json
Response:
{
  "events": [
    {
      "id": "event_456",
      "external_id": "google_event_123",
      "calendar_source": "google",
      "title": "Design Review",
      "description": "Review new mockups",
      "start_time": "2025-01-31T14:00:00Z",
      "end_time": "2025-01-31T15:00:00Z",
      "location": "Conference Room A",
      "linked_notes": ["note_abc123"],
      "linked_tasks": ["task_789"]
    }
  ]
}
```

#### POST /api/calendar/sync
Trigger calendar synchronization
```json
Response:
{
  "synced_events": 15,
  "created": 3,
  "updated": 10,
  "deleted": 2,
  "last_sync": "2025-01-30T20:00:00Z"
}
```

#### POST /api/calendar/events
Create a new calendar event (writes back to Google/Outlook)
```json
Request:
{
  "title": "New Meeting",
  "start_time": "2025-02-01T10:00:00Z",
  "end_time": "2025-02-01T11:00:00Z",
  "description": "Discuss project timeline"
}

Response: Event object with external_id
```

#### PUT /api/calendar/events/{event_id}
Update calendar event (syncs to Google/Outlook)
```json
Request:
{
  "title": "Updated Meeting Title",
  "start_time": "2025-02-01T14:00:00Z"
}

Response: Updated event object
```

#### GET /api/calendar/settings
```json
Response:
{
  "calendar_source": "google",
  "sync_enabled": true,
  "selected_calendars": ["primary", "work"],
  "sync_range_past_days": 30,
  "sync_range_future_days": 90
}
```

#### PUT /api/calendar/settings
```json
Request:
{
  "calendar_source": "google",
  "sync_enabled": true,
  "selected_calendars": ["primary"],
  "sync_range_past_days": 30,
  "sync_range_future_days": 90
}

Response: Updated settings
```

### Search

#### GET /api/search
Query parameters:
- `q`: Search query
- `type`: Filter by type (notes, tasks, journal, all)
- `limit`: Results per type

```json
Response:
{
  "notes": [
    {
      "id": "note_abc123",
      "title": "Meeting Notes",
      "preview": "...design components...",
      "relevance_score": 0.95
    }
  ],
  "tasks": []
}
```

#### GET /api/tags
```json
Response:
{
  "tags": [
    {"name": "design", "count": 15},
    {"name": "meetings", "count": 8},
    {"name": "planning", "count": 5}
  ]
}
```

### Dashboard

#### GET /api/dashboard/today
```json
Response:
{
  "date": "2025-01-30",
  "calendar_events": [...],      // Today's events
  "tasks_due": [...],            // Tasks due today
  "tasks_linked_to_events": [...],  // Tasks for today's meetings
  "recent_notes": [...],         // Notes from last 7 days (including any journal-style entries)
  "suggestions": [               // AI-generated (if enabled)
    {
      "type": "task",
      "title": "Review deck before 2pm meeting",
      "context": "You have 'Q4 Review' at 2pm",
      "confidence": 0.9
    }
  ]
}
```

### AI Features (When Enabled)

#### POST /api/ai/chat
Used for chat blocks within notes
```json
Request:
{
  "note_id": "note_abc123",
  "message": "Help me think through this problem"
}

Response:
{
  "response": "Let's break this down. What's the core issue you're facing?",
  "updated_content": null  // Note content if AI suggests edits
}
```

#### POST /api/ai/analyze-note/{note_id}
Manually trigger AI analysis (normally happens automatically)
```json
Response:
{
  "suggested_tags": ["design", "architecture"],
  "extracted_tasks": [
    "Review component specs",
    "Schedule follow-up meeting"
  ],
  "linked_events": ["event_456"]
}
```

#### GET /api/ai/suggestions/daily
```json
Response:
{
  "tasks": [
    {
      "title": "Prepare for design review",
      "reason": "You have 'Design Review' at 2pm today",
      "confidence": 0.85
    }
  ],
  "notes": [
    {
      "title": "Follow up on project timeline",
      "reason": "Mentioned in yesterday's journal",
      "confidence": 0.7
    }
  ]
}
```

### Settings

#### GET /api/settings
```json
Response:
{
  "ai_enabled": false,
  "ai_auto_tag": true,
  "ai_auto_extract_tasks": true,
  "calendar_source": "google",
  "calendar_sync_enabled": true,
  "theme": "light"
}
```

#### PUT /api/settings
```json
Request:
{
  "ai_enabled": true,
  "theme": "dark"
}

Response: Updated settings
```

## WebSocket

### Connection: ws://localhost:8000/ws
```json
// After connecting, client receives real-time updates:

{
  "type": "tags_added",
  "note_id": "note_abc123",
  "new_tags": ["design", "architecture"]
}

{
  "type": "tasks_extracted",
  "note_id": "note_abc123",
  "tasks": [
    {"id": "task_new1", "title": "Review specs", "ai_suggested": true}
  ]
}

{
  "type": "calendar_synced",
  "synced_events": 5
}

{
  "type": "suggestion",
  "suggestion": {
    "type": "task",
    "title": "Prepare for meeting",
    "context": "Design Review in 2 hours"
  }
}
```

## Services Implementation

### File Service (`services/file_service.py`)

**Responsibilities:**
- Read/write markdown files with YAML frontmatter
- Generate human-readable filenames from titles
- Handle file path conflicts (increment suffix if exists)
- Parse frontmatter and content separately
- Update frontmatter when metadata changes

**Key Functions:**
```python
def create_note_file(note_id: str, title: str, content: str, metadata: dict, created_at: datetime) -> str:
    """Create markdown file in date directory, return filepath"""
    # Extract date: YYYY-MM-DD
    # Create directory: notes/YYYY-MM-DD/
    # Generate filename: slugified-title.md
    # Return: notes/YYYY-MM-DD/slugified-title.md
    
def read_note_file(filepath: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, content_string)"""
    
def update_note_file(filepath: str, content: str = None, metadata: dict = None):
    """Update file, preserve what's not changed"""
    
def generate_filename(title: str) -> str:
    """Generate: slugified-title.md"""
    
def get_date_directory(date: datetime) -> str:
    """Generate: notes/YYYY-MM-DD/"""
```

### Link Parser (`services/link_parser.py`)

**Responsibilities:**
- Parse `[[note-title]]`, `[[task:id]]`, `[[event:id]]` from markdown
- Find and link note references
- Update link tables in database
- Generate backlink queries

**Key Functions:**
```python
def parse_links(content: str) -> dict:
    """Extract all [[link]] references"""
    
def resolve_note_links(links: list[str], db: Session) -> list[str]:
    """Convert [[title]] to note IDs"""
    
def update_note_links(note_id: str, content: str, db: Session):
    """Parse content and update link tables"""
```

### Calendar Sync (`services/calendar_sync.py`)

**Responsibilities:**
- Authenticate with Google Calendar or Outlook API
- Fetch events within configured date range
- Create/update/delete local calendar_events records
- Push local changes back to calendar provider
- Handle sync conflicts (last-write-wins)

**Key Functions:**
```python
async def sync_calendar(calendar_source: str, settings: dict, db: Session) -> dict:
    """Full sync, return statistics"""
    
async def create_external_event(event_data: dict, calendar_source: str) -> str:
    """Create event in Google/Outlook, return external_id"""
    
async def update_external_event(external_id: str, event_data: dict):
    """Update event in calendar provider"""
```

### AI Service (`services/ai_service.py`)

**Responsibilities:**
- Wrapper around Anthropic Claude API
- Extract tags from note content
- Extract actionable tasks
- Detect calendar event references
- Provide conversational journal chat
- Generate daily suggestions

**Key Functions:**
```python
async def extract_tags(content: str) -> list[str]:
    """Return 3-5 relevant tags"""
    
async def extract_tasks(content: str) -> list[str]:
    """Return actionable items"""
    
async def detect_event_references(content: str, upcoming_events: list) -> list[str]:
    """Match content to calendar events"""
    
async def chat_with_note(note_id: str, message: str, context: str) -> str:
    """Conversational chat within a note (for chat blocks)"""
    
async def generate_daily_suggestions(calendar: list, tasks: list, notes: list) -> dict:
    """Context-aware daily prep suggestions"""
```

## Background Tasks

### Processing Queue
All AI operations run as background tasks using FastAPI's `BackgroundTasks`:

```python
@app.post("/api/notes")
async def create_note(note: NoteCreate, background_tasks: BackgroundTasks):
    # Save note immediately
    saved_note = note_service.create(note)
    
    # Queue AI processing if enabled
    if settings.ai_enabled:
        background_tasks.add_task(process_note_ai, saved_note.id)
    
    return saved_note

async def process_note_ai(note_id: str):
    # Extract tags
    # Extract tasks
    # Link events
    # Send WebSocket updates
```

### Calendar Sync Job
Periodic sync using APScheduler or similar:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=15)
async def sync_calendar_job():
    if settings.calendar_sync_enabled:
        await calendar_sync.sync_calendar(...)
```

## Authentication

### JWT Token Flow
1. User POSTs to `/api/auth/login` with credentials
2. Backend verifies against stored hash (bcrypt)
3. Generate JWT token with 24-hour expiration
4. Frontend stores token in localStorage
5. Include `Authorization: Bearer {token}` header in all requests
6. Backend validates token on protected routes

### Security Considerations
- Single-user system: simple password hash in settings table
- HTTPS required in production
- CORS configured for frontend domain only
- Rate limiting on login endpoint (prevent brute force)
- Token refresh not needed (24-hour expiration acceptable)

## Error Handling

### Standard Error Response Format
```json
{
  "detail": "Note not found",
  "error_code": "NOTE_NOT_FOUND",
  "status_code": 404
}
```

### Common Error Codes
- `AUTH_REQUIRED`: 401, missing/invalid token
- `NOT_FOUND`: 404, resource doesn't exist
- `VALIDATION_ERROR`: 422, invalid request data
- `CONFLICT`: 409, duplicate resource (e.g., journal entry for date exists)
- `AI_UNAVAILABLE`: 503, Claude API error or disabled
- `SYNC_ERROR`: 500, calendar sync failed

## Testing Strategy

### Phase 1: Backend Testing
```bash
# Test with curl/httpie
http POST localhost:8000/api/notes title="Test" content="Content"
http GET localhost:8000/api/notes

# Verify database
sqlite3 database.db "SELECT * FROM notes;"

# Verify files created
ls notes/
cat notes/2025-01-30-test.md
```

### Test Fixtures
```python
# tests/fixtures/sample_data.py
def create_test_note():
    return {
        "title": "Test Meeting",
        "content": "# Notes\n\nAction: [[task:123]]",
        "tags": ["test"]
    }
```

## Deployment Considerations

### Environment Variables
```bash
DATABASE_URL=sqlite:///./workspace/database.db
WORKSPACE_PATH=/home/user/workspace
SECRET_KEY=your-secret-key-here
CLAUDE_API_KEY=sk-ant-...  # Optional
GOOGLE_CLIENT_ID=...       # For calendar sync
GOOGLE_CLIENT_SECRET=...
```

### Production Checklist
- [ ] HTTPS enabled
- [ ] CORS configured
- [ ] JWT secret key set (random, secure)
- [ ] Database backups scheduled
- [ ] File system backups scheduled
- [ ] Calendar sync credentials secured
- [ ] Rate limiting enabled
- [ ] Logs configured (errors to file)
- [ ] Process manager (systemd/supervisor)
