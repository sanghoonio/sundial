from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.task import Task, TaskChecklist, TaskNote

# Sentinel to distinguish "not provided" from explicit None
_UNSET: Any = object()


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Convert datetime to UTC. Naive datetimes are assumed to be UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def create_task(
    db: AsyncSession,
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: datetime | None = None,
    project_id: str = "proj_inbox",
    milestone_id: str | None = None,
    calendar_event_id: str | None = None,
    checklist: list[dict] | None = None,
    note_ids: list[str] | None = None,
) -> Task:
    # Get next position in milestone
    pos_result = await db.execute(
        select(func.coalesce(func.max(Task.position), -1))
        .where(Task.milestone_id == milestone_id)
    )
    next_pos = pos_result.scalar() + 1

    task = Task(
        title=title,
        description=description,
        priority=priority,
        due_date=_ensure_utc(due_date),
        project_id=project_id,
        milestone_id=milestone_id,
        calendar_event_id=calendar_event_id,
        position=next_pos,
    )
    db.add(task)
    await db.flush()

    if checklist:
        for i, item in enumerate(checklist):
            db.add(TaskChecklist(
                task_id=task.id,
                text=item["text"],
                is_checked=item.get("is_checked", False),
                position=i,
            ))

    if note_ids:
        for note_id in note_ids:
            db.add(TaskNote(task_id=task.id, note_id=note_id))

    await db.commit()
    await db.refresh(task, attribute_names=["checklist", "notes"])
    return task


async def get_task(db: AsyncSession, task_id: str) -> Task | None:
    result = await db.execute(
        select(Task).where(Task.id == task_id).options(
            selectinload(Task.checklist),
            selectinload(Task.notes)
        )
    )
    return result.scalar_one_or_none()


async def list_tasks(
    db: AsyncSession,
    project_id: str | None = None,
    milestone_id: str | None = None,
    status: str | None = None,
    ai_suggested: bool | None = None,
    due_after: datetime | None = None,
    due_before: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Task], int]:
    query = select(Task).options(selectinload(Task.checklist), selectinload(Task.notes)).order_by(Task.position)

    if project_id:
        query = query.where(Task.project_id == project_id)
    if milestone_id:
        query = query.where(Task.milestone_id == milestone_id)
    if status:
        query = query.where(Task.status == status)
    if ai_suggested is not None:
        query = query.where(Task.ai_suggested == ai_suggested)
    if due_after:
        query = query.where(Task.due_date >= due_after)
    if due_before:
        query = query.where(Task.due_date <= due_before)

    count_query = select(func.count()).select_from(Task)
    if project_id:
        count_query = count_query.where(Task.project_id == project_id)
    if status:
        count_query = count_query.where(Task.status == status)
    if ai_suggested is not None:
        count_query = count_query.where(Task.ai_suggested == ai_suggested)
    if due_after:
        count_query = count_query.where(Task.due_date >= due_after)
    if due_before:
        count_query = count_query.where(Task.due_date <= due_before)

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    result = await db.execute(query.offset(offset).limit(limit))
    tasks = list(result.scalars().all())
    return tasks, total


async def update_task(
    db: AsyncSession,
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_date: datetime | None = _UNSET,
    project_id: str | None = None,
    milestone_id: str | None = _UNSET,
    checklist: list[dict] | None = None,
    note_ids: list[str] | None = None,
) -> Task | None:
    task = await get_task(db, task_id)
    if task is None:
        return None

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if status is not None:
        task.status = status
        if status == "done":
            task.completed_at = datetime.now(timezone.utc)
        elif task.completed_at is not None:
            task.completed_at = None
    if priority is not None:
        task.priority = priority
    if due_date is not _UNSET:
        task.due_date = _ensure_utc(due_date)
    project_changed = False
    if project_id is not None:
        project_changed = project_id != task.project_id
        task.project_id = project_id
        if project_changed:
            task.milestone_id = None
    if milestone_id is not _UNSET:
        # If project just changed, validate milestone belongs to the new project
        if project_changed and milestone_id is not None:
            from api.models.project import ProjectMilestone
            result = await db.execute(
                select(ProjectMilestone.id).where(
                    ProjectMilestone.id == milestone_id,
                    ProjectMilestone.project_id == task.project_id,
                )
            )
            if result.scalar_one_or_none() is not None:
                task.milestone_id = milestone_id
            # else: silently ignore stale milestone_id
        else:
            task.milestone_id = milestone_id

    if checklist is not None:
        # Replace checklist items
        for item in task.checklist:
            await db.delete(item)
        await db.flush()
        for i, item in enumerate(checklist):
            db.add(TaskChecklist(
                task_id=task.id,
                text=item["text"],
                is_checked=item.get("is_checked", False),
                position=i,
            ))

    if note_ids is not None:
        # Replace note links
        for note_link in task.notes:
            await db.delete(note_link)
        await db.flush()
        for note_id in note_ids:
            db.add(TaskNote(task_id=task.id, note_id=note_id))

    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task, attribute_names=["checklist", "notes"])
    return task


async def move_task(db: AsyncSession, task_id: str, milestone_id: str | None, position: int = 0) -> Task | None:
    task = await get_task(db, task_id)
    if task is None:
        return None

    task.milestone_id = milestone_id
    task.position = position
    task.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task, attribute_names=["checklist", "notes"])
    return task


async def delete_task(db: AsyncSession, task_id: str) -> bool:
    task = await get_task(db, task_id)
    if task is None:
        return False
    await db.delete(task)
    await db.commit()
    return True
