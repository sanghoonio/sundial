from datetime import datetime, timezone

from sqlalchemy import delete, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.note import Note, NoteLink, NoteTag, Tag
from api.services.file_service import build_filepath, delete_note_file, write_note_file
from api.services.link_parser import parse_links


import re


def fts5_prefix_query(raw: str) -> str:
    """Convert a user search string into an FTS5 prefix query.

    Tokenizes on whitespace, strips non-alphanumeric characters,
    appends * for prefix matching, and joins with AND (implicit in FTS5).
    Case-insensitive by default in FTS5's unicode61 tokenizer.
    """
    tokens = raw.strip().split()
    clean = [re.sub(r"[^\w]", "", t) for t in tokens]
    clean = [t for t in clean if t]
    if not clean:
        return ""
    return " ".join(f"{t}*" for t in clean)


# --- FTS5 manual sync helpers ---

async def _fts_insert(db: AsyncSession, note_id: str, title: str, content: str, tags: list[str]) -> None:
    tags_str = " ".join(tags) if tags else ""
    await db.execute(
        text("INSERT INTO notes_fts(id, title, content, tags) VALUES (:id, :title, :content, :tags)"),
        {"id": note_id, "title": title, "content": content, "tags": tags_str},
    )


async def _fts_update(db: AsyncSession, note_id: str, title: str, content: str, tags: list[str]) -> None:
    await _fts_delete(db, note_id)
    await _fts_insert(db, note_id, title, content, tags)


async def _fts_delete(db: AsyncSession, note_id: str) -> None:
    await db.execute(
        text("DELETE FROM notes_fts WHERE id = :id"),
        {"id": note_id},
    )


# --- Tag helpers ---

async def _get_or_create_tags(db: AsyncSession, tag_names: list[str]) -> list[Tag]:
    tags = []
    for name in tag_names:
        name = name.strip().lower()
        if not name:
            continue
        result = await db.execute(select(Tag).where(Tag.name == name))
        tag = result.scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            await db.flush()
        tags.append(tag)
    return tags


async def _sync_note_tags(db: AsyncSession, note_id: str, tag_names: list[str]) -> None:
    """Replace all tags for a note using explicit junction table operations."""
    # Get current tag IDs before removing associations
    old_result = await db.execute(select(NoteTag.tag_id).where(NoteTag.note_id == note_id))
    old_tag_ids = [row[0] for row in old_result.fetchall()]

    await db.execute(delete(NoteTag).where(NoteTag.note_id == note_id))
    tag_objects = await _get_or_create_tags(db, tag_names)
    new_tag_ids = {tag.id for tag in tag_objects}
    for tag in tag_objects:
        db.add(NoteTag(note_id=note_id, tag_id=tag.id))

    # Clean up orphaned tags (old tags no longer used by any note)
    removed_ids = [tid for tid in old_tag_ids if tid not in new_tag_ids]
    for tag_id in removed_ids:
        count_result = await db.execute(
            select(func.count()).select_from(NoteTag).where(NoteTag.tag_id == tag_id)
        )
        if count_result.scalar() == 0:
            await db.execute(delete(Tag).where(Tag.id == tag_id))


# --- CRUD ---

async def create_note(db: AsyncSession, title: str, content: str = "", tags: list[str] | None = None, project_id: str | None = None) -> Note:
    now = datetime.now(timezone.utc)
    base_filepath = build_filepath(title, now)

    # Check for duplicate filepath and append suffix if needed
    filepath = base_filepath
    suffix = 1
    while True:
        result = await db.execute(select(Note).where(Note.filepath == filepath))
        if result.scalar_one_or_none() is None:
            break
        # Insert suffix before .md extension
        filepath = base_filepath[:-3] + f"-{suffix}.md"
        suffix += 1

    note = Note(title=title, filepath=filepath, content=content, project_id=project_id, created_at=now, updated_at=now)
    db.add(note)
    await db.flush()

    if tags:
        await _sync_note_tags(db, note.id, tags)

    # Parse and store wiki-links
    await _update_links(db, note, content)

    # Write markdown file
    write_note_file(
        filepath=filepath,
        note_id=note.id,
        title=title,
        content=content,
        created_at=now,
        updated_at=now,
        tags=tags or [],
        project_id=project_id,
    )

    # Update FTS index
    await _fts_insert(db, note.id, title, content, tags or [])

    await db.commit()

    # Re-fetch with eager-loaded tags
    return await get_note(db, note.id)


async def get_note(db: AsyncSession, note_id: str) -> Note | None:
    result = await db.execute(
        select(Note)
        .where(Note.id == note_id)
        .options(
            selectinload(Note.tags),
            selectinload(Note.calendar_links),
            selectinload(Note.incoming_links),
        )
    )
    return result.scalar_one_or_none()


async def get_note_by_title(db: AsyncSession, title: str) -> Note | None:
    result = await db.execute(
        select(Note).where(Note.title == title).options(selectinload(Note.tags))
    )
    return result.scalar_one_or_none()


async def list_notes(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    project_id: str | None = None,
    tag: str | None = None,
    tags: list[str] | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[Note], int]:
    # If search is provided, use FTS5 to get matching note IDs first
    fts_note_ids: list[str] | None = None
    if search:
        fts_q = fts5_prefix_query(search)
        if not fts_q:
            return [], 0
        fts_result = await db.execute(
            text("SELECT id FROM notes_fts WHERE notes_fts MATCH :query ORDER BY rank LIMIT 500"),
            {"query": fts_q},
        )
        fts_note_ids = [row[0] for row in fts_result.fetchall()]
        if not fts_note_ids:
            return [], 0

    query = select(Note).options(selectinload(Note.tags)).order_by(Note.updated_at.desc())
    count_query = select(func.count()).select_from(Note)

    if fts_note_ids is not None:
        query = query.where(Note.id.in_(fts_note_ids))
        count_query = count_query.where(Note.id.in_(fts_note_ids))

    if project_id:
        query = query.where(Note.project_id == project_id)
        count_query = count_query.where(Note.project_id == project_id)
    if tag:
        query = query.join(NoteTag).join(Tag).where(Tag.name == tag.lower())
        count_query = count_query.join(NoteTag).join(Tag).where(Tag.name == tag.lower())
    if tags:
        # Multi-tag filter: note must have ALL specified tags
        for t in tags:
            tag_alias = NoteTag.__table__.alias()
            tag_obj_alias = Tag.__table__.alias()
            query = query.where(
                Note.id.in_(
                    select(tag_alias.c.note_id)
                    .join(tag_obj_alias, tag_alias.c.tag_id == tag_obj_alias.c.id)
                    .where(tag_obj_alias.c.name == t.strip().lower())
                )
            )
            count_query = count_query.where(
                Note.id.in_(
                    select(tag_alias.c.note_id)
                    .join(tag_obj_alias, tag_alias.c.tag_id == tag_obj_alias.c.id)
                    .where(tag_obj_alias.c.name == t.strip().lower())
                )
            )
    if date_from:
        query = query.where(Note.created_at >= date_from)
        count_query = count_query.where(Note.created_at >= date_from)
    if date_to:
        query = query.where(Note.created_at <= date_to)
        count_query = count_query.where(Note.created_at <= date_to)

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    result = await db.execute(query.offset(offset).limit(limit))
    notes = list(result.scalars().all())
    return notes, total


async def update_note(db: AsyncSession, note_id: str, title: str | None = None, content: str | None = None, tags: list[str] | None = None, project_id: str | None = None) -> Note | None:
    note = await get_note(db, note_id)
    if note is None:
        return None

    now = datetime.now(timezone.utc)

    if title is not None:
        note.title = title
    if content is not None:
        note.content = content
        await _update_links(db, note, content)
    if tags is not None:
        await _sync_note_tags(db, note.id, tags)
    if project_id is not None:
        note.project_id = project_id

    note.updated_at = now

    # Determine tag names for file sync
    if tags is not None:
        tag_names = tags
    else:
        tag_names = [t.name for t in note.tags]

    # Query linked tasks and events for frontmatter enrichment
    from api.models.task import TaskNote
    task_result = await db.execute(select(TaskNote.task_id).where(TaskNote.note_id == note.id))
    linked_task_ids = [row[0] for row in task_result.fetchall()]

    linked_event_ids = [cl.event_id for cl in note.calendar_links]

    write_note_file(
        filepath=note.filepath,
        note_id=note.id,
        title=note.title,
        content=note.content,
        created_at=note.created_at,
        updated_at=now,
        tags=tag_names,
        project_id=note.project_id,
        linked_tasks=linked_task_ids if linked_task_ids else None,
        linked_events=linked_event_ids if linked_event_ids else None,
    )

    # Update FTS index
    await _fts_update(db, note.id, note.title, note.content, tag_names)

    note_id = note.id
    await db.commit()

    # Expire cached state so re-fetch loads fresh tags
    db.expire_all()
    return await get_note(db, note_id)


async def patch_note_content(db: AsyncSession, note_id: str, operations: list[dict]) -> Note:
    """Apply line-based patch operations to a note's content.

    Each operation has start_line, end_line, content.  Lines are 1-indexed.
    - Replace: start_line <= end_line — replaces lines[start..end] with content
    - Delete:  start_line <= end_line, content="" — removes those lines
    - Insert:  start_line > end_line — inserts content before start_line
    """
    note = await get_note(db, note_id)
    if note is None:
        raise ValueError(f"Note '{note_id}' not found.")

    lines = (note.content or "").split("\n")
    num_lines = len(lines)

    # Validate all operations first
    for i, op in enumerate(operations):
        s, e = op["start_line"], op["end_line"]
        is_insert = s > e
        if is_insert:
            # Insert: end_line is the anchor, must be in [0, num_lines]
            # end_line=0 means insert at the very beginning
            if e < 0 or e > num_lines:
                raise ValueError(f"Operation {i}: end_line {e} out of range (0-{num_lines}).")
            if s != e + 1:
                raise ValueError(f"Operation {i}: for insert, start_line must be end_line + 1.")
        else:
            if s < 1 or s > num_lines:
                raise ValueError(f"Operation {i}: start_line {s} out of range (1-{num_lines}).")
            if e < 1 or e > num_lines:
                raise ValueError(f"Operation {i}: end_line {e} out of range (1-{num_lines}).")

    # Check for overlapping operations
    # Normalize each op to an affected range for overlap detection
    ranges = []
    for i, op in enumerate(operations):
        s, e = op["start_line"], op["end_line"]
        if s > e:
            # Insert at position s — affects no existing lines, but we track
            # the insertion point to prevent two inserts at the same spot
            ranges.append((s, s, i))
        else:
            ranges.append((s, e, i))

    ranges.sort(key=lambda r: (r[0], r[1]))
    for j in range(len(ranges) - 1):
        _, end_a, idx_a = ranges[j]
        start_b, _, idx_b = ranges[j + 1]
        if end_a >= start_b:
            raise ValueError(
                f"Operations {idx_a} and {idx_b} overlap (lines {end_a} and {start_b})."
            )

    # Sort operations by start_line descending for bottom-to-top application
    sorted_ops = sorted(operations, key=lambda op: op["start_line"], reverse=True)

    for op in sorted_ops:
        s, e, content = op["start_line"], op["end_line"], op["content"]
        new_lines = content.split("\n") if content else []

        if s > e:
            # Insert before line s (after line e)
            lines[e:e] = new_lines
        else:
            # Replace lines[s-1:e] with new content
            lines[s - 1:e] = new_lines

    patched_content = "\n".join(lines)
    return await update_note(db, note_id, content=patched_content)


async def delete_note(db: AsyncSession, note_id: str) -> bool:
    note = await get_note(db, note_id)
    if note is None:
        return False

    # Get tag IDs before deletion to check for orphans
    result = await db.execute(
        select(NoteTag.tag_id).where(NoteTag.note_id == note_id)
    )
    tag_ids = [row[0] for row in result.all()]

    delete_note_file(note.filepath)

    # Remove from FTS index
    await _fts_delete(db, note_id)

    await db.delete(note)
    await db.commit()

    # Clean up orphaned tags (tags with no remaining notes)
    if tag_ids:
        for tag_id in tag_ids:
            count_result = await db.execute(
                select(func.count()).select_from(NoteTag).where(NoteTag.tag_id == tag_id)
            )
            if count_result.scalar() == 0:
                await db.execute(delete(Tag).where(Tag.id == tag_id))
        await db.commit()

    return True


async def get_backlinks(db: AsyncSession, note_id: str) -> list[Note]:
    result = await db.execute(
        select(Note)
        .join(NoteLink, NoteLink.source_note_id == Note.id)
        .where(NoteLink.target_note_id == note_id)
    )
    return list(result.scalars().all())


async def _update_links(db: AsyncSession, note: Note, content: str) -> None:
    # Remove existing outgoing links
    await db.execute(
        delete(NoteLink).where(NoteLink.source_note_id == note.id)
    )

    links = parse_links(content)
    for link_data in links:
        identifier = link_data["identifier"]
        link_type = link_data["link_type"]

        target_note_id = None
        if link_type == "note":
            target = await get_note_by_title(db, identifier)
            if target:
                target_note_id = target.id

        db.add(NoteLink(
            source_note_id=note.id,
            target_note_id=target_note_id,
            target_identifier=identifier,
            link_type=link_type,
        ))
