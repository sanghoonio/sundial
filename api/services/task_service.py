from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.task import Task, TaskChecklist
from api.models.project import ProjectMilestone


async def create_task(
    db: AsyncSession,
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: datetime | None = None,
    project_id: str = "proj_inbox",
    milestone_id: str | None = None,
    source_note_id: str | None = None,
    calendar_event_id: str | None = None,
    checklist: list[dict] | None = None,
) -> Task:
    # If no milestone specified, use the first milestone of the project
    if milestone_id is None:
        result = await db.execute(
            select(ProjectMilestone)
            .where(ProjectMilestone.project_id == project_id)
            .order_by(ProjectMilestone.position)
            .limit(1)
        )
        first_milestone = result.scalar_one_or_none()
        if first_milestone:
            milestone_id = first_milestone.id

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
        due_date=due_date,
        project_id=project_id,
        milestone_id=milestone_id,
        source_note_id=source_note_id,
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

    await db.commit()
    await db.refresh(task, attribute_names=["checklist"])
    return task


async def get_task(db: AsyncSession, task_id: str) -> Task | None:
    result = await db.execute(
        select(Task).where(Task.id == task_id).options(selectinload(Task.checklist))
    )
    return result.scalar_one_or_none()


async def list_tasks(
    db: AsyncSession,
    project_id: str | None = None,
    milestone_id: str | None = None,
    status: str | None = None,
    due_after: datetime | None = None,
    due_before: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Task], int]:
    query = select(Task).options(selectinload(Task.checklist)).order_by(Task.position)

    if project_id:
        query = query.where(Task.project_id == project_id)
    if milestone_id:
        query = query.where(Task.milestone_id == milestone_id)
    if status:
        query = query.where(Task.status == status)
    if due_after:
        query = query.where(Task.due_date >= due_after)
    if due_before:
        query = query.where(Task.due_date <= due_before)

    count_query = select(func.count()).select_from(Task)
    if project_id:
        count_query = count_query.where(Task.project_id == project_id)
    if status:
        count_query = count_query.where(Task.status == status)
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
    due_date: datetime | None = None,
    project_id: str | None = None,
    milestone_id: str | None = None,
    checklist: list[dict] | None = None,
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
    if due_date is not None:
        task.due_date = due_date
    if project_id is not None:
        task.project_id = project_id
        task.milestone_id = None
    if milestone_id is not None:
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

    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task, attribute_names=["checklist"])
    return task


async def move_task(db: AsyncSession, task_id: str, milestone_id: str, position: int = 0) -> Task | None:
    task = await get_task(db, task_id)
    if task is None:
        return None

    task.milestone_id = milestone_id
    task.position = position
    task.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task, attribute_names=["checklist"])
    return task


async def delete_task(db: AsyncSession, task_id: str) -> bool:
    task = await get_task(db, task_id)
    if task is None:
        return False
    await db.delete(task)
    await db.commit()
    return True
