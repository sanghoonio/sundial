from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.schemas.task import ChecklistItemCreate, TaskCreate, TaskList, TaskMove, TaskResponse, TaskUpdate
from api.services import task_service
from api.utils.auth import get_current_user
from api.utils.websocket import manager

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    checklist = [item.model_dump() for item in body.checklist] if body.checklist else None
    task = await task_service.create_task(
        db,
        title=body.title,
        description=body.description,
        priority=body.priority,
        due_date=body.due_date,
        project_id=body.project_id,
        milestone_id=body.milestone_id,
        source_note_id=body.source_note_id,
        calendar_event_id=body.calendar_event_id,
        checklist=checklist,
    )
    resp = _task_to_response(task)
    await manager.broadcast("task_created", {"id": task.id, "title": task.title})
    return resp


@router.get("", response_model=TaskList)
async def list_tasks(
    project_id: str | None = Query(None),
    milestone_id: str | None = Query(None),
    task_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    tasks, total = await task_service.list_tasks(
        db, project_id=project_id, milestone_id=milestone_id, status=task_status, limit=limit, offset=offset,
    )
    return TaskList(tasks=[_task_to_response(t) for t in tasks], total=total)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, body: TaskUpdate, db: AsyncSession = Depends(get_db)):
    checklist = [item.model_dump() for item in body.checklist] if body.checklist is not None else None
    task = await task_service.update_task(
        db, task_id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        due_date=body.due_date,
        project_id=body.project_id,
        milestone_id=body.milestone_id,
        checklist=checklist,
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    resp = _task_to_response(task)
    await manager.broadcast("task_updated", {"id": task.id, "title": task.title})
    return resp


@router.put("/{task_id}/move", response_model=TaskResponse)
async def move_task(task_id: str, body: TaskMove, db: AsyncSession = Depends(get_db)):
    task = await task_service.move_task(db, task_id, milestone_id=body.milestone_id, position=body.position)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    resp = _task_to_response(task)
    await manager.broadcast("task_updated", {"id": task.id, "title": task.title})
    return resp


@router.post("/{task_id}/checklist", response_model=TaskResponse)
async def update_checklist(task_id: str, items: list[ChecklistItemCreate], db: AsyncSession = Depends(get_db)):
    checklist = [item.model_dump() for item in items]
    task = await task_service.update_task(db, task_id, checklist=checklist)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    resp = _task_to_response(task)
    await manager.broadcast("task_updated", {"id": task.id, "title": task.title})
    return resp


@router.post("/{task_id}/accept", response_model=TaskResponse)
async def accept_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.ai_suggested = False
    await db.commit()
    await db.refresh(task, attribute_names=["checklist"])
    resp = _task_to_response(task)
    await manager.broadcast("task_updated", {"id": task.id, "title": task.title})
    return resp


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await task_service.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    await manager.broadcast("task_deleted", {"id": task_id})


def _task_to_response(task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        project_id=task.project_id,
        milestone_id=task.milestone_id,
        source_note_id=task.source_note_id,
        calendar_event_id=task.calendar_event_id,
        ai_suggested=task.ai_suggested or False,
        position=task.position,
        completed_at=task.completed_at,
        checklist=[
            {"id": c.id, "text": c.text, "is_checked": c.is_checked, "position": c.position}
            for c in task.checklist
        ],
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
