# Database Specification

## Architecture

### Hybrid Storage Model
- **SQLite**: Metadata, relationships, indexes, calendar events, tasks, projects
- **File System**: Note and journal content as markdown files with YAML frontmatter
- **Benefits**: Portability (markdown), performance (SQL queries), data integrity (relationships)

## File System Structure

```
workspace/
├── notes/
│   ├── 2025-01-30/
│   │   ├── meeting-with-design-team.md
│   │   ├── daily-journal.md
│   │   └── project-architecture-ideas.md
│   ├── 2025-01-29/
│   │   ├── weekly-review.md
│   │   └── bug-fixes.md
│   └── 2025-01-28/
│       └── team-standup.md
├── api/
│   └── (backend code)
├── ui/
│   └── (frontend code)
└── database.db
```

### Markdown File Format

**Note Example** (`notes/2025-01-30/meeting-with-design-team.md`):
```markdown
---
id: note_abc123xyz
title: Meeting with Design Team
created: 2025-01-30T14:30:00Z
updated: 2025-01-30T16:45:00Z
tags: [design, meetings, q1-planning]
linked_tasks: [task_789, task_012]
linked_events: [event_456]
project_id: proj_design_system
---

# Meeting Notes

Discussed the new component library approach...

## Action Items
- Review Figma designs by Friday
- Set up meeting with engineering team

## Chat Block
```chat
user: How should we prioritize these tasks?
assistant: Based on your calendar, the Figma review is more urgent since you have the engineering meeting scheduled for next week. I'd suggest tackling that first.
```

## Decisions
We decided to use Tailwind + custom components instead of a heavy UI framework.
```

**Journal-style Note Example** (`notes/2025-01-30/daily-reflection.md`):
```markdown
---
id: note_daily_20250130
title: Daily Reflection
created: 2025-01-30T20:00:00Z
updated: 2025-01-30T21:30:00Z
tags: [journal, reflection, planning]
linked_notes: [note_abc123xyz]
project_id: null
---

# January 30, 2025

Today was productive. Had a great meeting with the design team.

## Chat Block
```chat
user: I'm feeling overwhelmed about the project timeline
assistant: Let's break it down. What are the key milestones? When is the first deadline?
user: First deadline is end of Q1 for the prototype
assistant: That gives you 8 weeks. What can you delegate or defer to make that achievable?
```

## Reflection
After talking through it, I realize the timeline is actually reasonable if I focus on the MVP features first.
```

## SQLite Schema

### Core Tables

#### notes
```sql
CREATE TABLE notes (
    id TEXT PRIMARY KEY,              -- UUID: note_abc123xyz
    title TEXT NOT NULL,
    filepath TEXT NOT NULL UNIQUE,    -- notes/2025-01-30/meeting-with-design-team.md
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    project_id TEXT,                  -- Foreign key to projects
    is_archived BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX idx_notes_created ON notes(created_at DESC);
CREATE INDEX idx_notes_project ON notes(project_id);
CREATE INDEX idx_notes_archived ON notes(is_archived);
CREATE VIRTUAL TABLE notes_fts USING fts5(id, title, content, tags);
```

#### tags
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE note_tags (
    note_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    ai_suggested BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    
    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX idx_note_tags_note ON note_tags(note_id);
CREATE INDEX idx_note_tags_tag ON note_tags(tag_id);
```

#### projects
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,              -- proj_design_system
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',  -- active, paused, completed, archived
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP
);

CREATE TABLE project_milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,              -- Custom column name like "Research", "Prototype"
    position INTEGER NOT NULL,        -- Display order: 0, 1, 2...
    
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, title)
);

CREATE INDEX idx_milestones_project ON project_milestones(project_id, position);
```

#### tasks
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,              -- task_789
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo',  -- Maps to milestone or default status
    priority INTEGER DEFAULT 0,       -- 0=normal, 1=high, 2=urgent
    due_date DATE,
    
    project_id TEXT NOT NULL,
    milestone_id INTEGER,             -- NULL = uses default status
    source_note_id TEXT,              -- Note that created this task
    calendar_event_id TEXT,           -- Related calendar event
    
    ai_suggested BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (milestone_id) REFERENCES project_milestones(id) ON DELETE SET NULL,
    FOREIGN KEY (source_note_id) REFERENCES notes(id) ON DELETE SET NULL,
    FOREIGN KEY (calendar_event_id) REFERENCES calendar_events(id) ON DELETE SET NULL
);

CREATE TABLE task_checklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    item_text TEXT NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    position INTEGER NOT NULL,
    
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_ai_suggested ON tasks(ai_suggested);
```

#### calendar_events
```sql
CREATE TABLE calendar_events (
    id TEXT PRIMARY KEY,              -- event_456
    external_id TEXT UNIQUE,          -- ID from Google/Outlook
    calendar_source TEXT NOT NULL,    -- 'google' or 'outlook'
    calendar_id TEXT NOT NULL,        -- Which calendar (work, personal, etc.)
    
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    is_all_day BOOLEAN DEFAULT FALSE,
    
    synced_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE note_calendar_links (
    note_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    ai_suggested BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    
    PRIMARY KEY (note_id, event_id),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES calendar_events(id) ON DELETE CASCADE
);

CREATE INDEX idx_calendar_start ON calendar_events(start_time);
CREATE INDEX idx_calendar_external ON calendar_events(external_id);
```

### Linking Tables

#### note_links (Wiki-style links)
```sql
CREATE TABLE note_links (
    source_note_id TEXT NOT NULL,
    target_note_id TEXT NOT NULL,
    link_text TEXT,                   -- The [[text]] used in markdown
    created_at TIMESTAMP NOT NULL,
    
    PRIMARY KEY (source_note_id, target_note_id),
    FOREIGN KEY (source_note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_note_id) REFERENCES notes(id) ON DELETE CASCADE
);

CREATE INDEX idx_note_links_source ON note_links(source_note_id);
CREATE INDEX idx_note_links_target ON note_links(target_note_id);
```

### Configuration & Settings

#### user_settings
```sql
CREATE TABLE user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Settings stored here:
-- 'calendar_source': 'google' or 'outlook'
-- 'calendar_sync_enabled': 'true' or 'false'
-- 'calendar_sync_range_past_days': '30'
-- 'calendar_sync_range_future_days': '90'
-- 'selected_calendars': JSON array of calendar IDs
-- 'ai_enabled': 'true' or 'false'
-- 'ai_auto_tag': 'true' or 'false'
-- 'ai_auto_extract_tasks': 'true' or 'false'
```

#### ai_processing_queue
```sql
CREATE TABLE ai_processing_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,        -- 'note'
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,          -- 'auto_tag', 'extract_tasks', 'link_events'
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    created_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE INDEX idx_queue_status ON ai_processing_queue(status, created_at);
```

## Data Integrity Rules

### Cascading Deletes
- Delete project → tasks set to null or moved to "Inbox" project
- Delete note → tags/links/calendar links removed
- Delete task → checklist items removed
- Archive note → remains searchable, hidden from default views

### Unique Constraints
- Note filepath must be unique
- Journal entry date must be unique (one entry per day)
- Tag names must be unique (case-insensitive)
- External calendar event IDs must be unique per source

### Default Values
- New notes go to "Inbox" project if not specified
- New tasks default to "To Do" status/milestone
- All timestamps in UTC
- IDs use readable prefixes: `note_`, `task_`, `proj_`, `event_`, `journal_`

## Search & Query Patterns

### Full-Text Search
```sql
-- Search notes by content (uses FTS5)
SELECT n.* FROM notes n
JOIN notes_fts ON notes_fts.id = n.id
WHERE notes_fts MATCH 'design AND components'
ORDER BY rank;

-- Search by tag
SELECT n.* FROM notes n
JOIN note_tags nt ON n.id = nt.note_id
JOIN tags t ON nt.tag_id = t.id
WHERE t.name = 'meetings'
ORDER BY n.created_at DESC;

-- Search by date range
SELECT * FROM notes
WHERE created_at BETWEEN '2025-01-01' AND '2025-01-31'
ORDER BY created_at DESC;
```

### Context Queries
```sql
-- Get all context for today's dashboard
-- Calendar events today
SELECT * FROM calendar_events
WHERE DATE(start_time) = DATE('now')
ORDER BY start_time;

-- Tasks due today or linked to today's events
SELECT t.* FROM tasks t
LEFT JOIN calendar_events e ON t.calendar_event_id = e.id
WHERE t.due_date = DATE('now')
   OR DATE(e.start_time) = DATE('now')
ORDER BY t.priority DESC, t.due_date;

-- Recent notes about today's events
SELECT DISTINCT n.* FROM notes n
JOIN note_calendar_links ncl ON n.id = ncl.note_id
JOIN calendar_events e ON ncl.event_id = e.id
WHERE DATE(e.start_time) = DATE('now')
ORDER BY n.updated_at DESC;
```

### Backlinks
```sql
-- What notes link to this note?
SELECT n.* FROM notes n
JOIN note_links nl ON n.id = nl.source_note_id
WHERE nl.target_note_id = ?
ORDER BY n.updated_at DESC;

-- What tasks came from this note?
SELECT * FROM tasks
WHERE source_note_id = ?
ORDER BY created_at;
```

## File System Operations

### Note Creation
1. Generate ID: `note_` + short UUID
2. Extract date from created_at (or use today)
3. Create directory if not exists: `notes/YYYY-MM-DD/`
4. Create filename: `slugified-title.md`
5. Full filepath: `notes/YYYY-MM-DD/slugified-title.md`
6. Insert to SQLite with filepath
7. Write markdown file with frontmatter
8. Parse and index for full-text search
9. Extract and store tags, links

### Note Updates
1. Update SQLite `updated_at` timestamp
2. Update markdown file frontmatter
3. Reparse content for changed links/tags
4. Update full-text search index
5. Queue AI processing if enabled

### Sync Process
1. On startup: verify all files exist, rebuild missing records
2. On save: SQLite → filesystem (single source of truth: database)
3. Backup: copy entire workspace directory + database.db
4. Export: markdown files are already portable

## Migration Strategy

### Initial Setup
```sql
-- migrations/001_initial_schema.sql
-- Contains all CREATE TABLE statements

-- migrations/002_default_data.sql
INSERT INTO projects (id, title, description, status, created_at, updated_at)
VALUES ('proj_inbox', 'Inbox', 'Default project for uncategorized tasks', 'active', datetime('now'), datetime('now'));

INSERT INTO project_milestones (project_id, title, position)
VALUES 
    ('proj_inbox', 'To Do', 0),
    ('proj_inbox', 'In Progress', 1),
    ('proj_inbox', 'Done', 2);

INSERT INTO user_settings (key, value, updated_at)
VALUES 
    ('ai_enabled', 'false', datetime('now')),
    ('calendar_sync_enabled', 'false', datetime('now'));
```

### Future Migrations
- Use Alembic or simple numbered SQL files
- Version tracking in `schema_version` table
- Always keep backward compatibility with markdown files
