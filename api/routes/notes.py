from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.task import Task
from api.schemas.note import (
    BacklinkItem,
    BacklinkTaskItem,
    BacklinksResponse,
    BlockSchema,
    NoteCreate,
    NoteList,
    NoteListItem,
    NoteResponse,
    NoteUpdate,
)
from api.services import note_service
from api.services.block_parser import extract_markdown_text, parse_blocks, serialize_blocks
from api.utils.auth import get_current_user
from api.utils.websocket import manager

router = APIRouter(prefix="/notes", tags=["notes"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(body: NoteCreate, db: AsyncSession = Depends(get_db)):
    content = body.content
    if body.blocks is not None:
        content = serialize_blocks(body.blocks)
    note = await note_service.create_note(
        db, title=body.title, content=content, tags=body.tags, project_id=body.project_id,
    )
    resp = await _note_to_response(note, db)
    await manager.broadcast("note_created", {"id": note.id, "title": note.title})
    return resp


@router.get("", response_model=NoteList)
async def list_notes(
    project_id: str | None = Query(None),
    tag: str | None = Query(None),
    tags: str | None = Query(None, description="Comma-separated tag names for multi-tag filtering"),
    search: str | None = Query(None, description="FTS5 full-text search query"),
    date_from: datetime | None = Query(None, description="Filter notes created on or after this date"),
    date_to: datetime | None = Query(None, description="Filter notes created on or before this date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    notes, total = await note_service.list_notes(
        db, limit=limit, offset=offset, project_id=project_id, tag=tag,
        tags=tag_list, search=search, date_from=date_from, date_to=date_to,
    )
    return NoteList(
        notes=[await _note_to_list_item(n, db) for n in notes],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: str, db: AsyncSession = Depends(get_db)):
    note = await note_service.get_note(db, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return await _note_to_response(note, db)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: str, body: NoteUpdate, db: AsyncSession = Depends(get_db)):
    content = body.content
    if body.blocks is not None:
        content = serialize_blocks(body.blocks)
    note = await note_service.update_note(
        db, note_id, title=body.title, content=content, tags=body.tags, project_id=body.project_id,
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    resp = await _note_to_response(note, db)
    await manager.broadcast("note_updated", {"id": note.id, "title": note.title})
    return resp


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await note_service.delete_note(db, note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    await manager.broadcast("note_deleted", {"id": note_id})


@router.get("/{note_id}/backlinks", response_model=BacklinksResponse)
async def get_backlinks(note_id: str, db: AsyncSession = Depends(get_db)):
    note = await note_service.get_note(db, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    backlink_notes = await note_service.get_backlinks(db, note_id)

    # Also find tasks that reference this note via source_note_id
    task_result = await db.execute(
        select(Task).where(Task.source_note_id == note_id)
    )
    backlink_tasks = list(task_result.scalars().all())

    return BacklinksResponse(
        notes=[BacklinkItem(id=n.id, title=n.title, filepath=n.filepath) for n in backlink_notes],
        tasks=[BacklinkTaskItem(id=t.id, title=t.title, status=t.status) for t in backlink_tasks],
    )


async def _note_to_response(note, db: AsyncSession) -> NoteResponse:
    # Gather linked notes (from incoming_links)
    linked_notes = []
    if hasattr(note, "incoming_links") and note.incoming_links:
        linked_notes = [link.source_note_id for link in note.incoming_links if link.source_note_id]

    # Gather linked events (from calendar_links)
    linked_events = []
    if hasattr(note, "calendar_links") and note.calendar_links:
        linked_events = [cl.event_id for cl in note.calendar_links]

    # Gather linked tasks
    task_result = await db.execute(
        select(Task.id).where(Task.source_note_id == note.id)
    )
    linked_tasks = list(task_result.scalars().all())

    # Parse content into blocks
    blocks_raw = parse_blocks(note.content or "")
    blocks = [BlockSchema(**b) for b in blocks_raw]

    return NoteResponse(
        id=note.id,
        title=note.title,
        filepath=note.filepath,
        content=note.content or "",
        blocks=blocks,
        tags=[t.name for t in note.tags],
        project_id=note.project_id,
        is_archived=note.is_archived or False,
        linked_notes=linked_notes,
        linked_tasks=linked_tasks,
        linked_events=linked_events,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


async def _note_to_list_item(note, db: AsyncSession) -> NoteListItem:
    preview = ""
    if note.content:
        md_text = extract_markdown_text(note.content)
        preview = md_text[:200].strip()

    # Gather linked tasks
    task_result = await db.execute(
        select(Task.id).where(Task.source_note_id == note.id)
    )
    linked_tasks = list(task_result.scalars().all())

    return NoteListItem(
        id=note.id,
        title=note.title,
        filepath=note.filepath,
        tags=[t.name for t in note.tags],
        project_id=note.project_id,
        linked_tasks=linked_tasks,
        linked_events=[],
        preview=preview,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )
