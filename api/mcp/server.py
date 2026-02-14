"""MCP server definition for Sundial.

Exposes notes, tasks, and calendar events as MCP tools.
Tool handlers query the database directly via SQLAlchemy.
"""

import zoneinfo
from datetime import datetime, timedelta, timezone

from dateutil.rrule import rrulestr
from mcp.server import Server
from mcp.types import TextContent, Tool

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from api.database import async_session
from api.utils.websocket import manager
from api.models.calendar import CalendarEvent
from api.models.note import Note, NoteLink, NoteTag, Tag
from api.models.project import Project
from api.models.task import Task, TaskNote
from api.services.block_parser import extract_markdown_text
from api.services.note_service import create_note as service_create_note, update_note as service_update_note, patch_note_content as service_patch_note_content


async def _resolve_project(db, value: str) -> tuple[str | None, str | None]:
    """Resolve a project by ID or fuzzy name match.

    Returns (project_id, error_message). Exactly one will be non-None.
    """
    if not value or not value.strip():
        return None, None

    value = value.strip()

    # 1. Exact ID match
    project = await db.get(Project, value)
    if project:
        return project.id, None

    # 2. Case-insensitive exact name match
    result = await db.execute(
        select(Project).where(func.lower(Project.name) == value.lower())
    )
    project = result.scalar_one_or_none()
    if project:
        return project.id, None

    # 3. Substring match (name contains the query or query contains the name)
    result = await db.execute(select(Project).order_by(Project.name))
    all_projects = result.scalars().all()

    query_lower = value.lower()
    matches = []
    for p in all_projects:
        name_lower = p.name.lower()
        if query_lower in name_lower or name_lower in query_lower:
            matches.append(p)

    if len(matches) == 1:
        return matches[0].id, None

    if len(matches) > 1:
        options = ", ".join(f'"{p.name}" (id: {p.id})' for p in matches)
        return None, f"Ambiguous project '{value}'. Did you mean one of: {options}?"

    # 4. No match — list available projects
    if all_projects:
        options = ", ".join(f'"{p.name}" (id: {p.id})' for p in all_projects)
        return None, f"No project matching '{value}'. Available projects: {options}"
    return None, f"No project matching '{value}' and no projects exist yet."

mcp_server = Server("sundial")


def _parse_due_date(date_str: str) -> datetime:
    """Parse due date string, accepting ISO format with timezone or date-only.

    For full ISO strings with timezone (e.g., 2025-02-05T00:00:00-05:00),
    converts to UTC. For date-only strings (e.g., 2025-02-05), uses noon UTC
    as a safe default to avoid off-by-one-day errors across timezones.
    """
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is not None:
        # Has timezone - convert to UTC
        return dt.astimezone(timezone.utc)
    else:
        # Date-only (naive) - use noon UTC as safe default
        return dt.replace(hour=12, tzinfo=timezone.utc)


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
                    "status": {"type": "string", "description": "Filter by status (in_progress/done)", "enum": ["in_progress", "done"]},
                    "project_id": {"type": "string", "description": "Filter by project ID"},
                    "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                },
            },
        ),
        Tool(
            name="create_task",
            description="Create a new task in Sundial. Use note_ids to link the task to existing notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "description": "Priority: low/medium/high", "default": "medium"},
                    "due_date": {"type": "string", "description": "Due date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS±HH:MM with timezone)"},
                    "project_id": {"type": "string", "description": "Project ID (default: inbox)"},
                    "note_ids": {"type": "array", "items": {"type": "string"}, "description": "Note IDs to link to this task"},
                    "recurrence_rule": {"type": "string", "description": "Recurrence rule: 'daily', 'weekly', 'monthly', 'yearly', or a full RRULE string (e.g. FREQ=WEEKLY;COUNT=10)"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="update_task",
            description="Update an existing task. Use note_ids to replace linked notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "title": {"type": "string", "description": "New title"},
                    "status": {"type": "string", "description": "New status (in_progress/done)", "enum": ["in_progress", "done"]},
                    "priority": {"type": "string", "description": "New priority (low/medium/high)"},
                    "due_date": {"type": "string", "description": "New due date in ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS±HH:MM (or null to clear)"},
                    "note_ids": {"type": "array", "items": {"type": "string"}, "description": "Note IDs to link (replaces all existing links)"},
                    "recurrence_rule": {"type": "string", "description": "Recurrence rule: 'daily', 'weekly', 'monthly', 'yearly', or a full RRULE string. Set to empty string to remove recurrence."},
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
                "properties": {
                    "tz": {"type": "string", "description": "IANA timezone (e.g. America/New_York). If omitted, uses UTC."},
                },
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
                    "project": {"type": "string", "description": "Project name or ID to file the note under. Accepts partial or full project names."},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="update_note",
            description="Update an existing note's title, content, tags, or project. For small content edits, prefer patch_note instead — it accepts line-number-based operations so you don't need to resend the entire content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID to update"},
                    "title": {"type": "string", "description": "New title"},
                    "content": {"type": "string", "description": "New content in markdown"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Replace all tags with these"},
                    "project": {"type": "string", "description": "Project name or ID to move the note to. Accepts partial or full project names. Use empty string to unassign from project."},
                },
                "required": ["note_id"],
            },
        ),
        Tool(
            name="patch_note",
            description="Apply line-based edits to a note's content without resending the full text. Use this instead of update_note when making small changes to long notes. Read the note first to see line numbers, then send precise operations. Each operation specifies start_line, end_line (1-indexed), and replacement content. To replace lines: start_line <= end_line. To delete lines: set content to empty string. To insert: set start_line = end_line + 1 (inserts before start_line).",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID to patch"},
                    "operations": {
                        "type": "array",
                        "description": "List of line-based edit operations",
                        "items": {
                            "type": "object",
                            "properties": {
                                "start_line": {"type": "integer", "description": "Start line (1-indexed)"},
                                "end_line": {"type": "integer", "description": "End line (1-indexed)"},
                                "content": {"type": "string", "description": "Replacement content (use empty string to delete lines)"},
                            },
                            "required": ["start_line", "end_line", "content"],
                        },
                    },
                },
                "required": ["note_id", "operations"],
            },
        ),
        Tool(
            name="link_note_to_task",
            description="Link an existing note to an existing task. Creates a backlink without removing other linked notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to link to"},
                    "note_id": {"type": "string", "description": "Note ID to link"},
                },
                "required": ["task_id", "note_id"],
            },
        ),
        Tool(
            name="get_note_links",
            description="Get all links for a note: outgoing (this note links to) and incoming (links to this note). Includes linked notes, tasks, and events.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID"},
                },
                "required": ["note_id"],
            },
        ),
        Tool(
            name="get_task_links",
            description="Get all notes linked to a task, including both explicit links and wiki-link references ([[task:id]]).",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="delete_task",
            description="Delete a task by ID. Returns success or failure.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to delete"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="delete_note",
            description="Delete a note by ID. Removes the note file and cleans up orphaned tags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "Note ID to delete"},
                },
                "required": ["note_id"],
            },
        ),
        Tool(
            name="create_calendar_event",
            description="Create a new calendar event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title"},
                    "description": {"type": "string", "description": "Event description"},
                    "start_time": {"type": "string", "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)"},
                    "end_time": {"type": "string", "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)"},
                    "all_day": {"type": "boolean", "description": "Whether this is an all-day event", "default": False},
                    "location": {"type": "string", "description": "Event location"},
                },
                "required": ["title", "start_time"],
            },
        ),
        Tool(
            name="update_calendar_event",
            description="Update an existing calendar event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "Event ID to update"},
                    "title": {"type": "string", "description": "New title"},
                    "description": {"type": "string", "description": "New description"},
                    "start_time": {"type": "string", "description": "New start time in ISO format"},
                    "end_time": {"type": "string", "description": "New end time in ISO format"},
                    "all_day": {"type": "boolean", "description": "Whether this is an all-day event"},
                    "location": {"type": "string", "description": "New location"},
                },
                "required": ["event_id"],
            },
        ),
        Tool(
            name="delete_calendar_event",
            description="Delete a calendar event by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "Event ID to delete"},
                },
                "required": ["event_id"],
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
        elif name == "patch_note":
            return await _patch_note(db, arguments)
        elif name == "link_note_to_task":
            return await _link_note_to_task(db, arguments)
        elif name == "get_note_links":
            return await _get_note_links(db, arguments)
        elif name == "get_task_links":
            return await _get_task_links(db, arguments)
        elif name == "delete_task":
            return await _delete_task(db, arguments)
        elif name == "delete_note":
            return await _delete_note(db, arguments)
        elif name == "create_calendar_event":
            return await _create_calendar_event(db, arguments)
        elif name == "update_calendar_event":
            return await _update_calendar_event(db, arguments)
        elif name == "delete_calendar_event":
            return await _delete_calendar_event(db, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _search_notes(db, args: dict) -> list[TextContent]:
    from sqlalchemy import text

    query = args.get("query", "")
    limit = min(args.get("limit", 10), 50)

    if not query:
        return [TextContent(type="text", text="No query provided.")]

    from api.services.note_service import fts5_prefix_query
    fts_q = fts5_prefix_query(query)
    if not fts_q:
        return [TextContent(type="text", text=f"No notes found matching '{query}'.")]

    fts_result = await db.execute(
        text("SELECT id FROM notes_fts WHERE notes_fts MATCH :query ORDER BY rank LIMIT :limit"),
        {"query": fts_q, "limit": limit},
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

    from api.utils.recurrence import human_readable_rule

    lines = []
    for t in tasks:
        due = f", due: {t.due_date.strftime('%Y-%m-%d')}" if t.due_date else ""
        recur = f", {human_readable_rule(t.recurrence_rule)}" if t.recurrence_rule else ""
        lines.append(f"- [{t.status}] **{t.title}** (id: {t.id}, priority: {t.priority}{due}{recur})")

    return [TextContent(type="text", text=f"Found {len(tasks)} tasks:\n\n" + "\n".join(lines))]


async def _create_task(db, args: dict) -> list[TextContent]:
    from api.utils.recurrence import generate_series_id, normalize_rule, human_readable_rule

    title = args.get("title", "").strip()
    if not title:
        return [TextContent(type="text", text="Title is required.")]

    due_date = None
    if args.get("due_date"):
        try:
            due_date = _parse_due_date(args["due_date"])
        except ValueError:
            return [TextContent(type="text", text="Invalid due_date format. Use YYYY-MM-DD or full ISO 8601 with timezone.")]

    recurrence_rule = None
    if args.get("recurrence_rule"):
        recurrence_rule = normalize_rule(args["recurrence_rule"])

    # Get next position
    pos_result = await db.execute(select(func.coalesce(func.max(Task.position), -1)))
    next_pos = pos_result.scalar() + 1

    task = Task(
        title=title,
        description=args.get("description", ""),
        priority=args.get("priority", "medium"),
        due_date=due_date,
        project_id=args.get("project_id", "proj_inbox"),
        recurrence_rule=recurrence_rule,
        recurring_series_id=generate_series_id() if recurrence_rule else None,
        position=next_pos,
    )
    db.add(task)
    await db.flush()  # Get task.id before creating links

    # Link notes if provided
    note_ids = args.get("note_ids", [])
    linked_notes = []
    for note_id in note_ids:
        # Verify note exists
        note_result = await db.execute(select(Note).where(Note.id == note_id))
        note = note_result.scalar_one_or_none()
        if note:
            db.add(TaskNote(task_id=task.id, note_id=note_id))
            linked_notes.append(note.title)

    await db.commit()
    await db.refresh(task)
    await manager.broadcast("task_created", {"id": task.id, "title": task.title})

    result_text = f"Task created: **{task.title}** (id: {task.id})"
    if recurrence_rule:
        result_text += f"\nRecurrence: {human_readable_rule(recurrence_rule)}"
    if linked_notes:
        result_text += f"\nLinked notes: {', '.join(linked_notes)}"
    return [TextContent(type="text", text=result_text)]


async def _update_task(db, args: dict) -> list[TextContent]:
    from api.utils.recurrence import normalize_rule, generate_series_id, next_occurrence, human_readable_rule
    from api.models.task import TaskChecklist

    task_id = args.get("task_id", "")
    if not task_id:
        return [TextContent(type="text", text="task_id is required.")]

    result = await db.execute(
        select(Task).where(Task.id == task_id).options(
            selectinload(Task.notes),
            selectinload(Task.checklist),
        )
    )
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
    if "due_date" in args:
        if args["due_date"] is None:
            task.due_date = None
        else:
            try:
                task.due_date = _parse_due_date(args["due_date"])
            except ValueError:
                return [TextContent(type="text", text="Invalid due_date format. Use YYYY-MM-DD or full ISO 8601 with timezone.")]

    # Handle recurrence_rule
    if "recurrence_rule" in args:
        old_series_id = task.recurring_series_id
        rule_val = args["recurrence_rule"]
        if rule_val:
            task.recurrence_rule = normalize_rule(rule_val)
            if not task.recurring_series_id:
                task.recurring_series_id = generate_series_id()
        else:
            task.recurrence_rule = None
            task.recurring_series_id = None

        # Propagate recurrence change to all tasks in the same series
        if old_series_id:
            from sqlalchemy import update as sql_update
            await db.execute(
                sql_update(Task)
                .where(Task.recurring_series_id == old_series_id, Task.id != task.id)
                .values(
                    recurrence_rule=task.recurrence_rule,
                    recurring_series_id=task.recurring_series_id,
                )
            )

    # Handle note_ids: replace all linked notes
    linked_notes = []
    if "note_ids" in args:
        # Delete existing links
        for note_link in task.notes:
            await db.delete(note_link)
        await db.flush()

        # Create new links
        for note_id in args["note_ids"]:
            note_result = await db.execute(select(Note).where(Note.id == note_id))
            note = note_result.scalar_one_or_none()
            if note:
                db.add(TaskNote(task_id=task.id, note_id=note_id))
                linked_notes.append(note.title)

    task.updated_at = datetime.now(timezone.utc)

    # Spawn next recurring instance when completing a recurring task with a due date
    spawned_task = None
    if (
        args.get("status") == "done"
        and task.recurrence_rule
        and task.due_date
    ):
        next_due = next_occurrence(task.recurrence_rule, task.due_date)
        if next_due is not None:
            pos_result = await db.execute(
                select(func.coalesce(func.max(Task.position), -1))
                .where(Task.milestone_id == task.milestone_id)
            )
            next_pos = pos_result.scalar() + 1
            spawned_task = Task(
                title=task.title,
                description=task.description,
                priority=task.priority,
                due_date=next_due,
                project_id=task.project_id,
                milestone_id=task.milestone_id,
                recurrence_rule=task.recurrence_rule,
                recurring_series_id=task.recurring_series_id,
                position=next_pos,
            )
            db.add(spawned_task)
            await db.flush()
            # Copy checklist items (all unchecked)
            for item in task.checklist:
                db.add(TaskChecklist(
                    task_id=spawned_task.id,
                    text=item.text,
                    is_checked=False,
                    position=item.position,
                ))

    await db.commit()
    await manager.broadcast("task_updated", {"id": task.id, "title": task.title})

    result_text = f"Task updated: **{task.title}** (status: {task.status}, priority: {task.priority})"
    if task.recurrence_rule:
        result_text += f"\nRecurrence: {human_readable_rule(task.recurrence_rule)}"
    if spawned_task:
        due_str = spawned_task.due_date.strftime('%Y-%m-%d') if spawned_task.due_date else "no date"
        result_text += f"\nNext instance spawned: **{spawned_task.title}** (id: {spawned_task.id}, due: {due_str})"
    if "note_ids" in args:
        if linked_notes:
            result_text += f"\nLinked notes: {', '.join(linked_notes)}"
        else:
            result_text += "\nLinked notes: none"
    return [TextContent(type="text", text=result_text)]


async def _get_calendar_events(db, args: dict) -> list[TextContent]:
    try:
        start = datetime.strptime(args["start_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(args["end_date"], "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    except (KeyError, ValueError):
        return [TextContent(type="text", text="start_date and end_date are required in YYYY-MM-DD format.")]

    events_out = []

    # 1. Non-recurring events (no rrule, no recurring_event_id)
    non_recurring_result = await db.execute(
        select(CalendarEvent)
        .where(
            CalendarEvent.rrule.is_(None),
            CalendarEvent.recurring_event_id.is_(None),
            CalendarEvent.start_time >= start,
            CalendarEvent.start_time <= end,
        )
    )
    for e in non_recurring_result.scalars().all():
        events_out.append((e.start_time, e.title, e.end_time, e.all_day, e.location, e.id))

    # 2. Recurring masters - expand their RRULEs
    masters_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.rrule.isnot(None),
            CalendarEvent.recurring_event_id.is_(None),
        )
    )
    masters = masters_result.scalars().all()

    # 3. Exception instances in range
    exc_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.recurring_event_id.isnot(None),
            CalendarEvent.start_time >= start,
            CalendarEvent.start_time <= end,
        )
    )
    exceptions = exc_result.scalars().all()

    # Build exception map: master_id -> {recurrence_id -> exception}
    exc_by_master: dict[str, dict[str, CalendarEvent]] = {}
    for exc in exceptions:
        if exc.recurring_event_id not in exc_by_master:
            exc_by_master[exc.recurring_event_id] = {}
        if exc.recurrence_id:
            exc_by_master[exc.recurring_event_id][exc.recurrence_id] = exc

    # Expand each master
    for master in masters:
        try:
            duration = (master.end_time - master.start_time) if master.end_time else timedelta(hours=1)

            # Handle timezone-aware expansion
            orig_tz = None
            if master.original_timezone:
                try:
                    orig_tz = zoneinfo.ZoneInfo(master.original_timezone)
                except Exception:
                    pass

            if orig_tz:
                dtstart_utc = master.start_time
                if dtstart_utc.tzinfo is None:
                    dtstart_utc = dtstart_utc.replace(tzinfo=timezone.utc)
                dtstart_local = dtstart_utc.astimezone(orig_tz)
                local_start = start.astimezone(orig_tz)
                local_end = end.astimezone(orig_tz)
                rule = rrulestr(master.rrule, dtstart=dtstart_local)
                occurrences_local = rule.between(local_start, local_end, inc=True)
                occurrences = [occ.astimezone(timezone.utc) for occ in occurrences_local]
            else:
                dtstart = master.start_time
                if dtstart.tzinfo is None:
                    dtstart = dtstart.replace(tzinfo=timezone.utc)
                rule = rrulestr(master.rrule, dtstart=dtstart)
                occurrences = rule.between(start, end, inc=True)

            master_exceptions = exc_by_master.get(master.id, {})

            for occ_dt in occurrences:
                occ_iso = occ_dt.isoformat()
                if occ_iso in master_exceptions:
                    exc_event = master_exceptions[occ_iso]
                    events_out.append((exc_event.start_time, exc_event.title, exc_event.end_time, exc_event.all_day, exc_event.location, exc_event.id))
                else:
                    occ_end = occ_dt + duration
                    synthetic_id = f"{master.id}__rec__{occ_dt.strftime('%Y%m%dT%H%M%S')}"
                    events_out.append((occ_dt, master.title, occ_end, master.all_day, master.location, synthetic_id))
        except Exception:
            # If RRULE expansion fails, include the master event itself
            events_out.append((master.start_time, master.title, master.end_time, master.all_day, master.location, master.id))

    # Add any exceptions not already included (edge case: moved outside original date)
    included_ids = {e[5] for e in events_out}
    for exc in exceptions:
        if exc.id not in included_ids:
            events_out.append((exc.start_time, exc.title, exc.end_time, exc.all_day, exc.location, exc.id))

    # Sort by start time and limit
    events_out.sort(key=lambda e: e[0])
    events_out = events_out[:50]

    if not events_out:
        return [TextContent(type="text", text=f"No events between {args['start_date']} and {args['end_date']}.")]

    lines = []
    for start_time, title, end_time, all_day, location, event_id in events_out:
        time_str = start_time.strftime("%H:%M") if not all_day else "All day"
        end_str = f" - {end_time.strftime('%H:%M')}" if end_time and not all_day else ""
        location_str = f" @ {location}" if location else ""
        lines.append(f"- {start_time.strftime('%Y-%m-%d')} {time_str}{end_str}: **{title}**{location_str} (id: {event_id})")

    return [TextContent(type="text", text=f"Found {len(events_out)} events:\n\n" + "\n".join(lines))]


async def _get_dashboard(db, args: dict) -> list[TextContent]:
    tz_str = args.get("tz")
    if tz_str:
        try:
            user_tz = zoneinfo.ZoneInfo(tz_str)
        except (zoneinfo.ZoneInfoNotFoundError, KeyError):
            return [TextContent(type="text", text=f"Invalid timezone: {tz_str}")]
        now_local = datetime.now(user_tz)
        local_midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start = local_midnight.astimezone(timezone.utc)
        today_end = (local_midnight + timedelta(days=1)).astimezone(timezone.utc)
        local_date = local_midnight.strftime("%Y-%m-%d")
    else:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        local_date = today_start.strftime("%Y-%m-%d")
    seven_days_ago = today_start - timedelta(days=7)

    # Events - with proper recurring event expansion
    events_out = []

    # Non-recurring events today
    non_recurring_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.rrule.is_(None),
            CalendarEvent.recurring_event_id.is_(None),
            CalendarEvent.start_time >= today_start,
            CalendarEvent.start_time <= today_end,
        )
    )
    for e in non_recurring_result.scalars().all():
        events_out.append((e.start_time, e.title, e.all_day))

    # Recurring masters - expand to today
    masters_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.rrule.isnot(None),
            CalendarEvent.recurring_event_id.is_(None),
        )
    )
    masters = masters_result.scalars().all()

    # Exceptions today
    exc_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.recurring_event_id.isnot(None),
            CalendarEvent.start_time >= today_start,
            CalendarEvent.start_time <= today_end,
        )
    )
    exceptions = exc_result.scalars().all()
    exc_by_master: dict[str, dict[str, CalendarEvent]] = {}
    for exc in exceptions:
        if exc.recurring_event_id not in exc_by_master:
            exc_by_master[exc.recurring_event_id] = {}
        if exc.recurrence_id:
            exc_by_master[exc.recurring_event_id][exc.recurrence_id] = exc

    for master in masters:
        try:
            orig_tz = None
            if master.original_timezone:
                try:
                    orig_tz = zoneinfo.ZoneInfo(master.original_timezone)
                except Exception:
                    pass

            if orig_tz:
                dtstart_utc = master.start_time
                if dtstart_utc.tzinfo is None:
                    dtstart_utc = dtstart_utc.replace(tzinfo=timezone.utc)
                dtstart_local = dtstart_utc.astimezone(orig_tz)
                local_start = today_start.astimezone(orig_tz)
                local_end = today_end.astimezone(orig_tz)
                rule = rrulestr(master.rrule, dtstart=dtstart_local)
                occurrences_local = rule.between(local_start, local_end, inc=True)
                occurrences = [occ.astimezone(timezone.utc) for occ in occurrences_local]
            else:
                dtstart = master.start_time
                if dtstart.tzinfo is None:
                    dtstart = dtstart.replace(tzinfo=timezone.utc)
                rule = rrulestr(master.rrule, dtstart=dtstart)
                occurrences = rule.between(today_start, today_end, inc=True)

            master_exceptions = exc_by_master.get(master.id, {})
            for occ_dt in occurrences:
                occ_iso = occ_dt.isoformat()
                if occ_iso in master_exceptions:
                    exc_event = master_exceptions[occ_iso]
                    events_out.append((exc_event.start_time, exc_event.title, exc_event.all_day))
                else:
                    events_out.append((occ_dt, master.title, master.all_day))
        except Exception:
            pass

    # Sort and limit
    events_out.sort(key=lambda e: e[0])
    events_out = events_out[:10]

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

    parts = [f"# Dashboard for {local_date}\n"]

    if events_out:
        parts.append("## Today's Events")
        for start_time, title, all_day in events_out:
            time_str = start_time.strftime("%H:%M") if not all_day else "All day"
            parts.append(f"- {time_str}: {title}")
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

    # Resolve project by name or ID
    project_id = None
    project_ref = args.get("project") or args.get("project_id")
    if project_ref:
        project_id, error = await _resolve_project(db, project_ref)
        if error:
            return [TextContent(type="text", text=error)]

    note = await service_create_note(db, title=title, content=content, tags=tags, project_id=project_id)
    await manager.broadcast("note_created", {"id": note.id, "title": note.title})

    project_str = f" in project {project_id}" if project_id else ""
    return [TextContent(type="text", text=f"Note created: **{note.title}** (id: {note.id}){project_str}")]


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

    # Resolve project by name or ID; empty string means unassign
    project_id = None
    project_ref = args.get("project") if "project" in args else args.get("project_id")
    if project_ref:
        project_id, error = await _resolve_project(db, project_ref)
        if error:
            return [TextContent(type="text", text=error)]

    note = await service_update_note(
        db, note_id=note_id, title=title, content=content, tags=tags,
        project_id=project_id,
    )
    if note is None:
        return [TextContent(type="text", text=f"Failed to update note '{note_id}'.")]

    await manager.broadcast("note_updated", {"id": note.id, "title": note.title})
    tag_str = ", ".join(t.name for t in note.tags) if note.tags else "none"
    project_str = f"\nProject: {note.project_id}" if note.project_id else ""
    return [TextContent(type="text", text=f"Note updated: **{note.title}** (id: {note.id})\nTags: {tag_str}{project_str}")]


async def _patch_note(db, args: dict) -> list[TextContent]:
    note_id = args.get("note_id", "")
    if not note_id:
        return [TextContent(type="text", text="note_id is required.")]

    operations = args.get("operations", [])
    if not operations:
        return [TextContent(type="text", text="At least one operation is required.")]

    try:
        note = await service_patch_note_content(db, note_id, operations)
    except ValueError as e:
        return [TextContent(type="text", text=f"Patch failed: {e}")]

    await manager.broadcast("note_updated", {"id": note.id, "title": note.title})
    return [TextContent(type="text", text=f"Note patched: **{note.title}** (id: {note.id})\n{len(operations)} operation(s) applied.")]


async def _link_note_to_task(db, args: dict) -> list[TextContent]:
    task_id = args.get("task_id", "")
    note_id = args.get("note_id", "")

    if not task_id or not note_id:
        return [TextContent(type="text", text="Both task_id and note_id are required.")]

    # Verify task exists
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        return [TextContent(type="text", text=f"Task '{task_id}' not found.")]

    # Verify note exists
    note_result = await db.execute(select(Note).where(Note.id == note_id))
    note = note_result.scalar_one_or_none()
    if not note:
        return [TextContent(type="text", text=f"Note '{note_id}' not found.")]

    # Check if link already exists
    existing_link = await db.execute(
        select(TaskNote).where(TaskNote.task_id == task_id, TaskNote.note_id == note_id)
    )
    if existing_link.scalar_one_or_none():
        return [TextContent(type="text", text=f"Note **{note.title}** is already linked to task **{task.title}**.")]

    # Create the link
    db.add(TaskNote(task_id=task_id, note_id=note_id))
    await db.commit()
    await manager.broadcast("task_updated", {"id": task_id})

    return [TextContent(type="text", text=f"Linked note **{note.title}** to task **{task.title}**.")]


async def _get_note_links(db, args: dict) -> list[TextContent]:
    note_id = args.get("note_id", "")
    if not note_id:
        return [TextContent(type="text", text="note_id is required.")]

    # Verify note exists
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        return [TextContent(type="text", text=f"Note '{note_id}' not found.")]

    lines = [f"# Links for: {note.title}\n"]

    # --- Outgoing links (this note links TO these) ---
    lines.append("## Outgoing Links (this note links to)")

    # Outgoing note links
    outgoing_note_links = await db.execute(
        select(NoteLink).where(
            NoteLink.source_note_id == note_id,
            NoteLink.link_type == "note",
            NoteLink.target_note_id.isnot(None),
        )
    )
    outgoing_note_link_ids = [link.target_note_id for link in outgoing_note_links.scalars().all()]

    if outgoing_note_link_ids:
        outgoing_notes_result = await db.execute(
            select(Note).where(Note.id.in_(outgoing_note_link_ids))
        )
        outgoing_notes = outgoing_notes_result.scalars().all()
        for n in outgoing_notes:
            lines.append(f"- **Note:** {n.title} (id: {n.id})")
    else:
        lines.append("- No outgoing note links")

    # Outgoing task links
    outgoing_task_links = await db.execute(
        select(NoteLink).where(
            NoteLink.source_note_id == note_id,
            NoteLink.link_type == "task",
        )
    )
    outgoing_task_ids = [link.target_identifier for link in outgoing_task_links.scalars().all()]

    if outgoing_task_ids:
        outgoing_tasks_result = await db.execute(
            select(Task).where(Task.id.in_(outgoing_task_ids))
        )
        for t in outgoing_tasks_result.scalars().all():
            lines.append(f"- **Task:** {t.title} (id: {t.id}, status: {t.status})")

    # Outgoing event links
    from api.models.calendar import CalendarEvent
    outgoing_event_links = await db.execute(
        select(NoteLink).where(
            NoteLink.source_note_id == note_id,
            NoteLink.link_type == "event",
        )
    )
    outgoing_event_ids = [link.target_identifier for link in outgoing_event_links.scalars().all()]

    if outgoing_event_ids:
        outgoing_events_result = await db.execute(
            select(CalendarEvent).where(CalendarEvent.id.in_(outgoing_event_ids))
        )
        for e in outgoing_events_result.scalars().all():
            lines.append(f"- **Event:** {e.title} (id: {e.id})")

    # --- Incoming links (these link TO this note) ---
    lines.append("\n## Incoming Links (link to this note)")

    # Incoming note links (notes that link to this note via wiki-links)
    from api.services.note_service import get_backlinks
    incoming_notes = await get_backlinks(db, note_id)
    if incoming_notes:
        for n in incoming_notes:
            lines.append(f"- **Note:** {n.title} (id: {n.id})")
    else:
        lines.append("- No incoming note links")

    # Incoming task links via TaskNote table
    task_note_result = await db.execute(
        select(TaskNote).where(TaskNote.note_id == note_id)
    )
    linked_task_ids = [link.task_id for link in task_note_result.scalars().all()]

    if linked_task_ids:
        linked_tasks_result = await db.execute(
            select(Task).where(Task.id.in_(linked_task_ids))
        )
        for t in linked_tasks_result.scalars().all():
            lines.append(f"- **Task:** {t.title} (id: {t.id}, status: {t.status})")

    return [TextContent(type="text", text="\n".join(lines))]


async def _get_task_links(db, args: dict) -> list[TextContent]:
    task_id = args.get("task_id", "")
    if not task_id:
        return [TextContent(type="text", text="task_id is required.")]

    # Verify task exists
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return [TextContent(type="text", text=f"Task '{task_id}' not found.")]

    lines = [f"# Notes linked to task: {task.title}\n"]

    # 1. Explicit links via TaskNote table (from link_note_to_task or create_task(note_ids))
    explicit_link_result = await db.execute(
        select(TaskNote).where(TaskNote.task_id == task_id)
    )
    explicit_note_ids = [link.note_id for link in explicit_link_result.scalars().all()]

    explicit_notes = []
    if explicit_note_ids:
        explicit_notes_result = await db.execute(
            select(Note).where(Note.id.in_(explicit_note_ids))
        )
        explicit_notes = list(explicit_notes_result.scalars().all())

    # 2. Wiki-link references via NoteLink (notes with [[task:task_id]] in content)
    wikilink_result = await db.execute(
        select(NoteLink).where(
            NoteLink.link_type == "task",
            NoteLink.target_identifier == task_id,
        )
    )
    wikilink_note_ids = [link.source_note_id for link in wikilink_result.scalars().all()]

    wikilink_notes = []
    if wikilink_note_ids:
        # Exclude notes already in explicit links to avoid duplicates
        remaining_ids = [nid for nid in wikilink_note_ids if nid not in explicit_note_ids]
        if remaining_ids:
            wikilink_notes_result = await db.execute(
                select(Note).where(Note.id.in_(remaining_ids))
            )
            wikilink_notes = list(wikilink_notes_result.scalars().all())

    if explicit_notes:
        lines.append("## Explicitly linked notes")
        for n in explicit_notes:
            lines.append(f"- **{n.title}** (id: {n.id})")

    if wikilink_notes:
        lines.append("\n## Notes referencing this task (via [[task:...]])")
        for n in wikilink_notes:
            lines.append(f"- **{n.title}** (id: {n.id})")

    if not explicit_notes and not wikilink_notes:
        lines.append("No notes linked to this task.")

    return [TextContent(type="text", text="\n".join(lines))]


async def _delete_task(db, args: dict) -> list[TextContent]:
    task_id = args.get("task_id", "")
    if not task_id:
        return [TextContent(type="text", text="task_id is required.")]

    from api.services.task_service import delete_task
    success = await delete_task(db, task_id)

    if success:
        await manager.broadcast("task_deleted", {"id": task_id})
        return [TextContent(type="text", text=f"Task '{task_id}' deleted successfully.")]
    return [TextContent(type="text", text=f"Task '{task_id}' not found.")]


async def _delete_note(db, args: dict) -> list[TextContent]:
    note_id = args.get("note_id", "")
    if not note_id:
        return [TextContent(type="text", text="note_id is required.")]

    from api.services.note_service import delete_note
    success = await delete_note(db, note_id)

    if success:
        await manager.broadcast("note_deleted", {"id": note_id})
        return [TextContent(type="text", text=f"Note '{note_id}' deleted successfully.")]
    return [TextContent(type="text", text=f"Note '{note_id}' not found.")]


async def _create_calendar_event(db, args: dict) -> list[TextContent]:
    title = args.get("title", "").strip()
    if not title:
        return [TextContent(type="text", text="Title is required.")]

    start_time_str = args.get("start_time", "")
    if not start_time_str:
        return [TextContent(type="text", text="start_time is required.")]

    try:
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
    except ValueError:
        return [TextContent(type="text", text="Invalid start_time format. Use ISO format.")]

    end_time = None
    if args.get("end_time"):
        try:
            end_time = datetime.fromisoformat(args["end_time"].replace("Z", "+00:00"))
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
        except ValueError:
            return [TextContent(type="text", text="Invalid end_time format. Use ISO format.")]

    event = CalendarEvent(
        title=title,
        description=args.get("description", ""),
        start_time=start_time,
        end_time=end_time,
        all_day=args.get("all_day", False),
        location=args.get("location", ""),
        calendar_source="local",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    await manager.broadcast("event_created", {"id": event.id, "title": event.title})

    return [TextContent(type="text", text=f"Event created: **{event.title}** (id: {event.id})\nStart: {event.start_time}")]


async def _update_calendar_event(db, args: dict) -> list[TextContent]:
    event_id = args.get("event_id", "")
    if not event_id:
        return [TextContent(type="text", text="event_id is required.")]

    event = await db.get(CalendarEvent, event_id)
    if not event:
        return [TextContent(type="text", text=f"Event '{event_id}' not found.")]

    if "title" in args:
        event.title = args["title"]
    if "description" in args:
        event.description = args["description"]
    if "start_time" in args:
        try:
            start_time = datetime.fromisoformat(args["start_time"].replace("Z", "+00:00"))
            event.start_time = start_time.replace(tzinfo=timezone.utc) if start_time.tzinfo is None else start_time
        except ValueError:
            return [TextContent(type="text", text="Invalid start_time format.")]
    if "end_time" in args:
        try:
            end_time = datetime.fromisoformat(args["end_time"].replace("Z", "+00:00"))
            event.end_time = end_time.replace(tzinfo=timezone.utc) if end_time.tzinfo is None else end_time
        except ValueError:
            return [TextContent(type="text", text="Invalid end_time format.")]
    if "all_day" in args:
        event.all_day = args["all_day"]
    if "location" in args:
        event.location = args["location"]

    event.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await manager.broadcast("event_updated", {"id": event.id, "title": event.title})

    return [TextContent(type="text", text=f"Event updated: **{event.title}** (id: {event.id})")]


async def _delete_calendar_event(db, args: dict) -> list[TextContent]:
    event_id = args.get("event_id", "")
    if not event_id:
        return [TextContent(type="text", text="event_id is required.")]

    event = await db.get(CalendarEvent, event_id)
    if not event:
        return [TextContent(type="text", text=f"Event '{event_id}' not found.")]

    await db.delete(event)
    await db.commit()
    await manager.broadcast("event_deleted", {"id": event_id})

    return [TextContent(type="text", text=f"Event '{event_id}' deleted successfully.")]
