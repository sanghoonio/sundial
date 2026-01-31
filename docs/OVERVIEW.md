# Personal AI Workspace - Project Specification

## Overview

A self-hosted personal productivity workspace that combines notes, tasks, calendar integration, and journaling into a unified interface. The system works fully without AI, with optional AI enhancements that operate invisibly in the background to auto-tag notes, extract tasks, and provide conversational journaling assistance.

## Core Principles

1. **AI-Optional Architecture**: Full functionality without AI; enhancements are invisible background processes
2. **Data Portability**: Notes stored as markdown files with YAML frontmatter for easy export/backup
3. **Unified Context**: Deep linking between notes, tasks, calendar events, and projects
4. **Single-User Focus**: Simplified architecture for personal use on a self-hosted server
5. **Phased Implementation**: Backend-first approach allowing incremental development

## Tech Stack

### Backend (api/)
- **FastAPI** (Python): REST API server and static file host
- **SQLAlchemy**: ORM for database operations
- **SQLite**: Local database for metadata and relationships
- **Anthropic SDK**: Claude API integration (optional)
- **Google/Microsoft Graph API**: Calendar synchronization
- **WebSockets**: Real-time updates for AI enhancements

### Frontend (ui/)
- **Svelte**: Reactive UI framework
- **Vite**: Build tool (output served by FastAPI at root)
- **Tailwind CSS**: Utility-first styling
- **DaisyUI**: Component library (base layer)
- **Lucide Icons**: Icon set
- **Custom Components**: shadcn-inspired accessible primitives

### Storage
- **SQLite**: Metadata, relationships, indexes
- **File System**: Markdown files in date-based directories
- **Hybrid Approach**: Frontmatter in markdown + database indexing

## Key Features

### Notes System
- Markdown-based notes with YAML frontmatter
- Block-based editor supporting text blocks and chat blocks
- Wiki-style linking: `[[note-title]]`, `[[task:id]]`, `[[event:id]]`
- Full-text search across all content
- Automatic and manual tagging
- File storage: `notes/YYYY-MM-DD/slugified-title.md`
- Journal entries are simply notes (no separate system needed)

### Task Management (Kanban)
- Draggable tasks across customizable columns
- Default columns: To Do, In Progress, Done
- Projects can define custom milestone columns
- Minimal task structure: title, description, status, due date, subtask checklists
- Tasks link to source notes and calendar events
- AI-suggested tasks appear with reduced opacity and are easily dismissible

### Calendar Integration
- Bidirectional sync with Google Calendar or Outlook
- Read and write calendar events
- User-configurable sync settings (which calendars, date ranges)
- Automatic linking between calendar events and related notes/tasks
- Meeting preparation suggestions based on upcoming events

### Projects
- Container for related tasks
- Project description/overview
- Custom milestone columns (kanban buckets)
- Status tracking: active, paused, completed
- Archive functionality with searchable history

## AI Integration (Optional)

### Invisible Enhancements
- **Auto-tagging**: Extracts 3-5 relevant topic tags from note content
- **Task Extraction**: Identifies actionable items in notes, creates suggested tasks
- **Event Linking**: Detects calendar event references in notes
- **Daily Suggestions**: Context-aware recommendations based on calendar + tasks + notes

### Chat Blocks in Notes
- Chat blocks within any note (including journal-style entries)
- AI prompts and helps work through thoughts
- Conversation preserved in the note
- AI responses update the note content naturally

### Real-time Updates
- WebSocket connection for live updates
- Tags fade in after AI processing
- Toast notifications for extracted tasks
- No loading states or "AI thinking" indicators

### Behavior
- All AI processing happens in background tasks after immediate user response
- Suggestions visually distinct (reduced opacity, different color)
- Easy dismiss/accept actions
- No AI features implied in base interface

## Implementation Phases

### Phase 1: Backend + Database (Weeks 1-2)
- SQLite schema implementation
- Markdown file system setup
- FastAPI server with core CRUD endpoints
- Calendar sync implementation (read-only initially)
- Authentication (basic password)
- Test fixtures and API verification

### Phase 2: Basic Frontend (Weeks 3-4)
- Svelte app scaffolding
- Simple CRUD interfaces (forms, lists)
- Basic routing and navigation
- Plain textarea editors
- API integration and state management
- Core workflows functional

### Phase 3: UI Polish (Weeks 5-6)
- WYSIWYG markdown editor
- Block-based note system
- Drag-and-drop kanban
- Tailwind/DaisyUI styling implementation
- Custom component library
- Responsive mobile considerations
- Search and filtering UI

### Phase 4: AI Integration (Week 7+)
- Claude API integration
- Background task processing
- WebSocket real-time updates
- AI service functions (tagging, extraction, chat)
- Conversational journal interface
- Suggestion system UI

## User Experience Goals

### Without AI
- Fast, responsive note-taking
- Manual tagging and organization
- Clear task management
- Integrated calendar view
- Searchable knowledge base

### With AI
- Tags appear automatically seconds after saving
- Tasks extracted from meeting notes without prompting
- Journaling feels like talking to a thoughtful friend
- Daily prep suggestions based on context
- Everything feels slightly more intelligent, never in the way

## Data Flow Examples

### Creating a Meeting Note
1. User writes note about upcoming meeting
2. Note saved immediately to file + database
3. (If AI enabled) Background: tags extracted, calendar event linked, prep tasks suggested
4. User sees tags fade in, receives toast: "2 prep tasks added"
5. Tasks appear on kanban in "suggested" state

### Daily Dashboard View
1. User opens app
2. Sees today's calendar events (synced from Google)
3. Tasks due today or linked to meetings displayed
4. Recent notes from today and yesterday shown
5. (If AI enabled) AI suggests prep work: "Review Q4 deck before 2pm meeting"

### Note with AI Chat
1. User creates note
2. Adds text block: "Feeling stuck on the project architecture"
3. Adds chat block, types: "Help me think through this"
4. AI responds with questions and suggestions
5. Conversation preserved in note
6. User adds final text block summarizing decision

## Security & Privacy

- Single-user authentication (username/password)
- JWT tokens for API access
- HTTPS required for production deployment
- No sensitive financial/identity data handling
- Self-hosted: full data ownership
- Regular SQLite backups recommended

## Future Considerations (Out of Scope)

- Multi-user support
- Mobile native apps
- End-to-end encryption
- Git integration for version control
- Plugin/extension system
- Desktop app (Electron/Tauri)

## Success Criteria

- Can create, edit, search notes without friction
- Calendar stays synced reliably
- Tasks move smoothly between states
- All features work completely without AI
- AI enhancements feel natural, never forced
- Data remains portable (markdown files)
- System runs reliably on small VPS/home server
