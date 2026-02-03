"""MCP server definition for Sundial.

Exposes notes, tasks, and calendar events as MCP tools.
Tool handlers query the database directly via SQLAlchemy.
"""

from datetime import datetime, timedelta, timezone

from mcp.server import Server
from mcp.types import TextContent, Tool

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from api.database import async_session
from api.models.calendar import CalendarEvent
from api.models.note import Note, NoteTag, Tag
from api.models.project import Project
from api.models.task import Task
from api.services.block_parser import extract_markdown_text
from api.services.note_service import create_note as service_create_note, update_note as service_update_note

mcp_server = Server("sundial")


def _tool_list() -> list[Tool]:
    return [
        Tool(
            name="search_notes",
            description="Search notes by full-text query. Returns matching note titles and snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_note",
            description="Get a single note by ID. Returns title and full content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"},
                },
                "required": ["note_id"],
            },
        ),
        Tool(
            name="list_notes",
            description="List notes with optional filters. Returns titles, tags, and previews.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                    "tag": {"type": "string", "description": "Filter by tag name"},
                    "project_id": {"type": "string", "description": "Filter by project ID"},
                },
            },
        ),
        Tool(
            name="list_tasks",
            description="List tasks with optional filters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status (open/in_progress/done)", "enum": ["open", "in_progress", "done"]},
                    "project_id": {"type": "string", "description": "Filter by project ID"},
                    "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                },
            },
        ),
        Tool(
            name="create_task",
            description="Create a new task in Sundial.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "description": "Priority: low/medium/high", "default": "medium"},
                    "due_date": {"type": "string", "description": "Due date in ISO format (YYYY-MM-DD)"},
                    "project_id": {"type": "string", "description": "Project ID (default: inbox)"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="update_task",
            description="Update an existing task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "title": {"type": "string", "description": "New title"},
                    "status": {"type": "string", "description": "New status (open/in_progress/done)", "enum": ["open", "in_progress", "done"]},
                    "priority": {"type": "string", "description": "New priority (low/medium/high)"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="get_calendar_events",
            description="Get calendar events within a date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                },
                "required": ["start_date", "end_date"],
            },
        ),
        Tool(
            name="get_dashboard",
            description="Get today's dashboard: events, due tasks, and recent notes.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="list_projects",
            description="List all projects. Returns project IDs, names, status, and task counts.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="list_tags",
            description="List all tags with usage counts.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="create_note",
            description="Create a new note. Returns the created note ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Note content in markdown"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to apply"},
                    "project_id": {"type": "string", "description": "Project ID (default: none)"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="update_note",
            description="Update an existing note's title, content, or tags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID to update"},
                    "title": {"type": "string", "description": "New title"},
                    "content": {"type": "string", "description": "New content in markdown"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Replace all tags with these"},
                },
                "required": ["note_id"],
            },
        ),
    ]


@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return _tool_list()


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    async with async_session() as db:
        if name == "search_notes":
            return await _search_notes(db, arguments)
        elif name == "get_note":
            return await _get_note(db, arguments)
        elif name == "list_notes":
            return await _list_notes(db, arguments)
        elif name == "list_tasks":
            return await _list_tasks(db, arguments)
        elif name == "create_task":
            return await _create_task(db, arguments)
        elif name == "update_task":
            return await _update_task(db, arguments)
        elif name == "get_calendar_events":
            return await _get_calendar_events(db, arguments)
        elif name == "get_dashboard":
            return await _get_dashboard(db, arguments)
        elif name == "list_projects":
            return await _list_projects(db, arguments)
        elif name == "list_tags":
            return await _list_tags(db, arguments)
        elif name == "create_note":
            return await _create_note(db, arguments)
        elif name == "update_note":
            return await _update_note(db, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _search_notes(db, args: dict) -> list[TextContent]:
    from sqlalchemy import text

    query = args.get("query", "")
    limit = min(args.get("limit", 10), 50)

    if not query:
        return [TextContent(type="text", text="No query provided.")]

    fts_result = await db.execute(
        text("SELECT id FROM notes_fts WHERE notes_fts MATCH :query ORDER BY rank LIMIT :limit"),
        {"query": query, "limit": limit},
    )
    note_ids = [row[0] for row in fts_result.fetchall()]

    if not note_ids:
        return [TextContent(type="text", text=f"No notes found matching '{query}'.")]

    result = await db.execute(
        select(Note).where(Note.id.in_(note_ids)).options(selectinload(Note.tags))
    )
    notes = result.scalars().all()

    lines = []
    for note in notes:
        tags = ", ".join(t.name for t in note.tags) if note.tags else "none"
        preview = extract_markdown_text(note.content or "")[:200]
        lines.append(f"**{note.title}** (id: {note.id})\nTags: {tags}\n{preview}\n")

    return [TextContent(type="text", text="\n---\n".join(lines))]


async def _get_note(db, args: dict) -> list[TextContent]:
    note_id = args.get("note_id", "")
    if not note_id:
        return [TextContent(type="text", text="No note_id provided.")]

    result = await db.execute(
        select(Note).where(Note.id == note_id).options(selectinload(Note.tags))
    )
    note = result.scalar_one_or_none()

    if not note:
        return [TextContent(type="text", text=f"Note '{note_id}' not found.")]

    tags = ", ".join(t.name for t in note.tags) if note.tags else "none"
    content = extract_markdown_text(note.content or "")

    return [TextContent(
        type="text",
        text=f"# {note.title}\n\nID: {note.id}\nTags: {tags}\nCreated: {note.created_at}\nUpdated: {note.updated_at}\n\n{content}",
    )]


async def _list_notes(db, args: dict) -> list[TextContent]:
    limit = min(args.get("limit", 20), 50)
    tag = args.get("tag")
    project_id = args.get("project_id")

    query = select(Note).options(selectinload(Note.tags)).order_by(Note.updated_at.desc())

    if project_id:
        query = query.where(Note.project_id == project_id)
    if tag:
        query = query.join(NoteTag).join(Tag).where(Tag.name == tag.lower())

    result = await db.execute(query.limit(limit))
    notes = result.scalars().all()

    if not notes:
        return [TextContent(type="text", text="No notes found.")]

    lines = []
    for note in notes:
        tags = ", ".join(t.name for t in note.tags) if note.tags else ""
        line = f"- **{note.title}** (id: {note.id})"
        if tags:
            line += f" [{tags}]"
        lines.append(line)

    return [TextContent(type="text", text=f"Found {len(notes)} notes:\n\n" + "\n".join(lines))]


async def _list_tasks(db, args: dict) -> list[TextContent]:
    limit = min(args.get("limit", 20), 50)
    status_filter = args.get("status")
    project_id = args.get("project_id")

    query = select(Task).order_by(Task.priority.desc(), Task.created_at)

    if status_filter:
        query = query.where(Task.status == status_filter)
    if project_id:
        query = query.where(Task.project_id == project_id)

    result = await db.execute(query.limit(limit))
    tasks = result.scalars().all()

    if not tasks:
        return [TextContent(type="text", text="No tasks found.")]

    lines = []
    for t in tasks:
        due = f", due: {t.due_date.strftime('%Y-%m-%d')}" if t.due_date else ""
        lines.append(f"- [{t.status}] **{t.title}** (id: {t.id}, priority: {t.priority}{due})")

    return [TextContent(type="text", text=f"Found {len(tasks)} tasks:\n\n" + "\n".join(lines))]


async def _create_task(db, args: dict) -> list[TextContent]:
    title = args.get("title", "").strip()
    if not title:
        return [TextContent(type="text", text="Title is required.")]

    due_date = None
    if args.get("due_date"):
        try:
            due_date = datetime.strptime(args["due_date"], "%Y-%m-%d")
        except ValueError:
            return [TextContent(type="text", text="Invalid due_date format. Use YYYY-MM-DD.")]

    # Get next position
    pos_result = await db.execute(select(func.coalesce(func.max(Task.position), -1)))
    next_pos = pos_result.scalar() + 1

    task = Task(
        title=title,
        description=args.get("description", ""),
        priority=args.get("priority", "medium"),
        due_date=due_date,
        project_id=args.get("project_id", "proj_inbox"),
        position=next_pos,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return [TextContent(type="text", text=f"Task created: **{task.title}** (id: {task.id})")]


async def _update_task(db, args: dict) -> list[TextContent]:
    task_id = args.get("task_id", "")
    if not task_id:
        return [TextContent(type="text", text="task_id is required.")]

    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return [TextContent(type="text", text=f"Task '{task_id}' not found.")]

    if "title" in args:
        task.title = args["title"]
    if "status" in args:
        task.status = args["status"]
        if args["status"] == "done":
            task.completed_at = datetime.now(timezone.utc)
    if "priority" in args:
        task.priority = args["priority"]

    task.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return [TextContent(type="text", text=f"Task updated: **{task.title}** (status: {task.status}, priority: {task.priority})")]


async def _get_calendar_events(db, args: dict) -> list[TextContent]:
    try:
        start = datetime.strptime(args["start_date"], "%Y-%m-%d")
        end = datetime.strptime(args["end_date"], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except (KeyError, ValueError):
        return [TextContent(type="text", text="start_date and end_date are required in YYYY-MM-DD format.")]

    result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.start_time.between(start, end))
        .order_by(CalendarEvent.start_time)
        .limit(50)
    )
    events = result.scalars().all()

    if not events:
        return [TextContent(type="text", text=f"No events between {args['start_date']} and {args['end_date']}.")]

    lines = []
    for e in events:
        time_str = e.start_time.strftime("%H:%M") if not e.all_day else "All day"
        end_str = f" - {e.end_time.strftime('%H:%M')}" if e.end_time and not e.all_day else ""
        location = f" @ {e.location}" if e.location else ""
        lines.append(f"- {e.start_time.strftime('%Y-%m-%d')} {time_str}{end_str}: **{e.title}**{location} (id: {e.id})")

    return [TextContent(type="text", text=f"Found {len(events)} events:\n\n" + "\n".join(lines))]


async def _get_dashboard(db, args: dict) -> list[TextContent]:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    seven_days_ago = today_start - timedelta(days=7)

    # Events
    event_result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.start_time.between(today_start, today_end))
        .order_by(CalendarEvent.start_time)
        .limit(10)
    )
    events = event_result.scalars().all()

    # Due tasks
    task_result = await db.execute(
        select(Task)
        .where((Task.status != "done") & (Task.due_date.isnot(None)) & (Task.due_date <= today_end))
        .order_by(Task.priority.desc())
        .limit(10)
    )
    tasks_due = task_result.scalars().all()

    # Recent notes
    note_result = await db.execute(
        select(Note)
        .where(Note.updated_at >= seven_days_ago)
        .order_by(Note.updated_at.desc())
        .limit(5)
    )
    notes = note_result.scalars().all()

    parts = [f"# Dashboard for {today_start.strftime('%Y-%m-%d')}\n"]

    if events:
        parts.append("## Today's Events")
        for e in events:
            time_str = e.start_time.strftime("%H:%M") if not e.all_day else "All day"
            parts.append(f"- {time_str}: {e.title}")
    else:
        parts.append("## Today's Events\nNo events today.")

    if tasks_due:
        parts.append("\n## Tasks Due")
        for t in tasks_due:
            parts.append(f"- [{t.priority}] {t.title} (id: {t.id})")
    else:
        parts.append("\n## Tasks Due\nNo tasks due today.")

    if notes:
        parts.append("\n## Recent Notes")
        for n in notes:
            parts.append(f"- {n.title} (updated: {n.updated_at.strftime('%Y-%m-%d')})")

    return [TextContent(type="text", text="\n".join(parts))]


async def _list_projects(db, args: dict) -> list[TextContent]:
    result = await db.execute(
        select(Project).order_by(Project.name)
    )
    projects = result.scalars().all()

    if not projects:
        return [TextContent(type="text", text="No projects found.")]

    lines = []
    for p in projects:
        # Count tasks for this project
        task_count_result = await db.execute(
            select(func.count()).select_from(Task).where(Task.project_id == p.id)
        )
        task_count = task_count_result.scalar()

        desc = f" - {p.description[:50]}..." if p.description and len(p.description) > 50 else (f" - {p.description}" if p.description else "")
        lines.append(f"- **{p.name}** (id: {p.id}, status: {p.status}, tasks: {task_count}){desc}")

    return [TextContent(type="text", text=f"Found {len(projects)} projects:\n\n" + "\n".join(lines))]


async def _list_tags(db, args: dict) -> list[TextContent]:
    # Get all tags with note counts
    result = await db.execute(
        select(Tag, func.count(NoteTag.note_id).label("note_count"))
        .outerjoin(NoteTag, Tag.id == NoteTag.tag_id)
        .group_by(Tag.id)
        .order_by(Tag.name)
    )
    rows = result.all()

    if not rows:
        return [TextContent(type="text", text="No tags found.")]

    lines = []
    for tag, count in rows:
        lines.append(f"- **{tag.name}** ({count} notes)")

    return [TextContent(type="text", text=f"Found {len(rows)} tags:\n\n" + "\n".join(lines))]


async def _create_note(db, args: dict) -> list[TextContent]:
    title = args.get("title", "").strip()
    if not title:
        return [TextContent(type="text", text="Title is required.")]

    content = args.get("content", "")
    tags = args.get("tags", [])
    project_id = args.get("project_id")

    note = await service_create_note(db, title=title, content=content, tags=tags, project_id=project_id)

    return [TextContent(type="text", text=f"Note created: **{note.title}** (id: {note.id})")]


async def _update_note(db, args: dict) -> list[TextContent]:
    note_id = args.get("note_id", "")
    if not note_id:
        return [TextContent(type="text", text="note_id is required.")]

    # Check if note exists
    result = await db.execute(select(Note).where(Note.id == note_id))
    existing = result.scalar_one_or_none()
    if not existing:
        return [TextContent(type="text", text=f"Note '{note_id}' not found.")]

    title = args.get("title")
    content = args.get("content")
    tags = args.get("tags")

    note = await service_update_note(db, note_id=note_id, title=title, content=content, tags=tags)
    if note is None:
        return [TextContent(type="text", text=f"Failed to update note '{note_id}'.")]

    tag_str = ", ".join(t.name for t in note.tags) if note.tags else "none"
    return [TextContent(type="text", text=f"Note updated: **{note.title}** (id: {note.id})\nTags: {tag_str}")]
