import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session
from api.models.calendar import CalendarEvent, NoteCalendarLink
from api.models.note import Note, NoteTag, Tag
from api.models.settings import AIProcessingQueue, UserSettings
from api.models.task import Task
from api.services import ai_service
from api.services.block_parser import extract_markdown_text
from api.utils.websocket import manager

logger = logging.getLogger(__name__)

DEBOUNCE_SECONDS = 30


async def process_note_ai(note_id: str) -> None:
    """Main entry point for background AI processing on a note.

    Called from BackgroundTasks — runs in its own DB session.
    """
    async with async_session() as db:
        try:
            # Check AI enabled + API key configured
            config_result = await db.execute(
                select(UserSettings).where(
                    UserSettings.key.in_(["ai_enabled", "openrouter_api_key", "ai_auto_tag", "ai_auto_extract_tasks", "ai_auto_link_events"])
                )
            )
            config = {row.key: row.value for row in config_result.scalars().all()}

            if config.get("ai_enabled", "false").lower() != "true":
                return
            if not config.get("openrouter_api_key", ""):
                return

            # Debounce: check if this note was processed recently
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=DEBOUNCE_SECONDS)
            recent = await db.execute(
                select(AIProcessingQueue).where(
                    AIProcessingQueue.entity_id == note_id,
                    AIProcessingQueue.entity_type == "note",
                    AIProcessingQueue.created_at >= cutoff,
                    AIProcessingQueue.status.in_(["processing", "completed"]),
                )
            )
            if recent.scalar_one_or_none() is not None:
                logger.debug("Skipping AI for note %s (debounced)", note_id)
                return

            # Load note
            note_result = await db.execute(select(Note).where(Note.id == note_id))
            note = note_result.scalar_one_or_none()
            if not note or not note.content:
                return

            content = extract_markdown_text(note.content)
            if not content.strip():
                return

            # Run enabled operations
            if config.get("ai_auto_tag", "false").lower() == "true":
                await _run_auto_tag(db, note, content)

            if config.get("ai_auto_extract_tasks", "false").lower() == "true":
                await _run_extract_tasks(db, note, content)

            if config.get("ai_auto_link_events", "false").lower() == "true":
                await _run_link_events(db, note, content)

        except Exception:
            logger.exception("Background AI processing failed for note %s", note_id)


async def _run_auto_tag(db: AsyncSession, note: Note, content: str) -> None:
    """Auto-tag a note via AI."""
    queue_entry = AIProcessingQueue(
        entity_type="note", entity_id=note.id, operation="auto_tag", status="processing",
        started_at=datetime.now(timezone.utc),
    )
    db.add(queue_entry)
    await db.flush()

    try:
        # Get existing tags in system
        tag_result = await db.execute(select(Tag.name))
        existing_tags = [row[0] for row in tag_result.fetchall()]

        suggested = await ai_service.auto_tag(content, existing_tags, db)
        if not suggested:
            queue_entry.status = "completed"
            queue_entry.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # Get note's current tags
        current_tag_result = await db.execute(
            select(Tag.name).join(NoteTag).where(NoteTag.note_id == note.id)
        )
        current_tags = {row[0] for row in current_tag_result.fetchall()}

        new_tags = [t for t in suggested if t not in current_tags]
        if not new_tags:
            queue_entry.status = "completed"
            queue_entry.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # Add new tags
        for tag_name in new_tags:
            tag_result = await db.execute(select(Tag).where(Tag.name == tag_name))
            tag = tag_result.scalar_one_or_none()
            if tag is None:
                tag = Tag(name=tag_name)
                db.add(tag)
                await db.flush()
            db.add(NoteTag(note_id=note.id, tag_id=tag.id, ai_suggested=True))

        queue_entry.status = "completed"
        queue_entry.completed_at = datetime.now(timezone.utc)
        await db.commit()

        # Broadcast
        await manager.broadcast("ai_tags_suggested", {
            "note_id": note.id,
            "tags": new_tags,
        })

    except Exception as e:
        logger.exception("Auto-tag failed for note %s", note.id)
        queue_entry.status = "failed"
        queue_entry.error_message = str(e)
        queue_entry.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def _run_extract_tasks(db: AsyncSession, note: Note, content: str) -> None:
    """Extract tasks from note content via AI."""
    queue_entry = AIProcessingQueue(
        entity_type="note", entity_id=note.id, operation="extract_tasks", status="processing",
        started_at=datetime.now(timezone.utc),
    )
    db.add(queue_entry)
    await db.flush()

    try:
        suggested = await ai_service.extract_tasks(content, note.title, db)
        if not suggested:
            queue_entry.status = "completed"
            queue_entry.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        created_tasks = []
        for task_data in suggested:
            title = task_data.get("title", "").strip()
            if not title:
                continue

            # Check if a similar task already exists for this note
            existing = await db.execute(
                select(Task).where(Task.source_note_id == note.id, Task.title == title)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            # Get next position
            pos_result = await db.execute(
                select(func.coalesce(func.max(Task.position), -1))
            )
            next_pos = pos_result.scalar() + 1

            task = Task(
                title=title,
                description=task_data.get("description", ""),
                priority=task_data.get("priority", "medium"),
                source_note_id=note.id,
                ai_suggested=True,
                position=next_pos,
            )
            db.add(task)
            await db.flush()
            created_tasks.append({"id": task.id, "title": task.title})

        queue_entry.status = "completed"
        queue_entry.completed_at = datetime.now(timezone.utc)
        await db.commit()

        if created_tasks:
            await manager.broadcast("ai_tasks_extracted", {
                "note_id": note.id,
                "tasks": created_tasks,
            })

    except Exception as e:
        logger.exception("Extract tasks failed for note %s", note.id)
        queue_entry.status = "failed"
        queue_entry.error_message = str(e)
        queue_entry.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def _run_link_events(db: AsyncSession, note: Note, content: str) -> None:
    """Link note to relevant calendar events via AI."""
    queue_entry = AIProcessingQueue(
        entity_type="note", entity_id=note.id, operation="link_events", status="processing",
        started_at=datetime.now(timezone.utc),
    )
    db.add(queue_entry)
    await db.flush()

    try:
        # Fetch recent events (past 7 days + next 30 days)
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)
        end = now + timedelta(days=30)

        event_result = await db.execute(
            select(CalendarEvent)
            .where(CalendarEvent.start_time.between(start, end))
            .limit(50)
        )
        events_raw = event_result.scalars().all()
        if not events_raw:
            queue_entry.status = "completed"
            queue_entry.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        events = [
            {"id": e.id, "title": e.title, "description": e.description or "", "start_time": str(e.start_time)}
            for e in events_raw
        ]

        matched_ids = await ai_service.link_events(content, events, db)
        if not matched_ids:
            queue_entry.status = "completed"
            queue_entry.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # Validate IDs exist and not already linked
        valid_event_ids = {e.id for e in events_raw}
        existing_links_result = await db.execute(
            select(NoteCalendarLink.event_id).where(NoteCalendarLink.note_id == note.id)
        )
        existing_links = {row[0] for row in existing_links_result.fetchall()}

        new_links = [eid for eid in matched_ids if eid in valid_event_ids and eid not in existing_links]

        for event_id in new_links:
            db.add(NoteCalendarLink(
                note_id=note.id, event_id=event_id, ai_suggested=True,
            ))

        queue_entry.status = "completed"
        queue_entry.completed_at = datetime.now(timezone.utc)
        await db.commit()

        if new_links:
            await manager.broadcast("ai_events_linked", {
                "note_id": note.id,
                "event_ids": new_links,
            })

    except Exception as e:
        logger.exception("Link events failed for note %s", note.id)
        queue_entry.status = "failed"
        queue_entry.error_message = str(e)
        queue_entry.completed_at = datetime.now(timezone.utc)
        await db.commit()
