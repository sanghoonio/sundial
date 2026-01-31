from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.task import Task
from api.schemas.note import (
    BacklinkItem,
    BacklinkTaskItem,
    BacklinksResponse,
    NoteCreate,
    NoteList,
    NoteListItem,
    NoteResponse,
    NoteUpdate,
)
from api.services import note_service
from api.utils.auth import get_current_user
from api.utils.websocket import manager

router = APIRouter(prefix="/notes", tags=["notes"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(body: NoteCreate, db: AsyncSession = Depends(get_db)):
    note = await note_service.create_note(
        db, title=body.title, content=body.content, tags=body.tags, project_id=body.project_id,
    )
    resp = _note_to_response(note)
    await manager.broadcast("note_created", {"id": note.id, "title": note.title})
    return resp


@router.get("", response_model=NoteList)
async def list_notes(
    project_id: str | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    notes, total = await note_service.list_notes(db, limit=limit, offset=offset, project_id=project_id, tag=tag)
    return NoteList(
        notes=[_note_to_list_item(n) for n in notes],
        total=total,
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: str, db: AsyncSession = Depends(get_db)):
    note = await note_service.get_note(db, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return _note_to_response(note)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: str, body: NoteUpdate, db: AsyncSession = Depends(get_db)):
    note = await note_service.update_note(
        db, note_id, title=body.title, content=body.content, tags=body.tags, project_id=body.project_id,
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    resp = _note_to_response(note)
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


def _note_to_response(note) -> NoteResponse:
    # Gather linked notes (from incoming_links)
    linked_notes = []
    if hasattr(note, "incoming_links") and note.incoming_links:
        linked_notes = [link.source_note_id for link in note.incoming_links if link.source_note_id]

    # Gather linked events (from calendar_links)
    linked_events = []
    if hasattr(note, "calendar_links") and note.calendar_links:
        linked_events = [cl.event_id for cl in note.calendar_links]

    return NoteResponse(
        id=note.id,
        title=note.title,
        filepath=note.filepath,
        content=note.content,
        tags=[t.name for t in note.tags],
        project_id=note.project_id,
        is_archived=note.is_archived or False,
        linked_notes=linked_notes,
        linked_tasks=[],  # Populated by caller if needed, or via backlinks
        linked_events=linked_events,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def _note_to_list_item(note) -> NoteListItem:
    preview = ""
    if note.content:
        preview = note.content[:200].strip()

    return NoteListItem(
        id=note.id,
        title=note.title,
        filepath=note.filepath,
        tags=[t.name for t in note.tags],
        project_id=note.project_id,
        linked_tasks=[],
        linked_events=[],
        preview=preview,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )
