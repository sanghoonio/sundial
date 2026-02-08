from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database import get_db
from api.models.project import Project, ProjectMilestone
from api.models.task import Task
from api.schemas.project import MilestoneUpdate, ProjectCreate, ProjectList, ProjectReorder, ProjectResponse, ProjectUpdate
from api.utils.auth import get_current_user
from api.utils.websocket import manager

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.get(Project, body.id)
    if existing:
        raise HTTPException(status_code=400, detail="Project ID already exists")

    # Place new project at the end of the list
    max_pos_result = await db.execute(select(func.coalesce(func.max(Project.position), -1)))
    next_position = max_pos_result.scalar() + 1

    project = Project(id=body.id, name=body.name, description=body.description, color=body.color, icon=body.icon, position=next_position)
    db.add(project)
    await db.flush()

    for i, ms in enumerate(body.milestones):
        db.add(ProjectMilestone(project_id=project.id, name=ms.name, position=ms.position or i))

    # If no milestones given, create defaults
    if not body.milestones:
        for i, name in enumerate(["To Do", "In Progress"]):
            db.add(ProjectMilestone(project_id=project.id, name=name, position=i))

    await db.commit()
    return await _get_project_response(db, project.id)


@router.get("", response_model=ProjectList)
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).options(selectinload(Project.milestones)).order_by(Project.position, Project.created_at)
    )
    projects = list(result.scalars().all())

    responses = []
    for p in projects:
        responses.append(await _project_to_response(db, p))

    return ProjectList(
        projects=responses,
        total=len(projects),
    )


@router.put("/reorder", response_model=ProjectList)
async def reorder_projects(body: ProjectReorder, db: AsyncSession = Depends(get_db)):
    """Reorder projects by providing the full list of project IDs in desired order."""
    for i, project_id in enumerate(body.project_ids):
        project = await db.get(Project, project_id)
        if project:
            project.position = i
    await db.commit()
    return await list_projects(db)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    resp = await _get_project_response(db, project_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return resp


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, body: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    if body.color is not None:
        project.color = body.color
    if body.icon is not None:
        project.icon = body.icon
    if body.status is not None:
        project.status = body.status
        if body.status == "completed":
            project.completed_at = datetime.now(timezone.utc)
        elif project.completed_at is not None and body.status != "completed":
            project.completed_at = None

    await db.commit()
    resp = await _get_project_response(db, project_id)
    await manager.broadcast("project_updated", {"id": project_id, "name": project.name})
    return resp


@router.put("/{project_id}/milestones", response_model=ProjectResponse)
async def update_milestones(project_id: str, body: MilestoneUpdate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get existing milestones
    result = await db.execute(
        select(ProjectMilestone).where(ProjectMilestone.project_id == project_id)
    )
    old_milestones = {ms.id: ms for ms in result.scalars().all()}

    # Track which IDs are in the new list
    new_ids = set()

    for i, ms in enumerate(body.milestones):
        if ms.id and ms.id in old_milestones:
            # Update existing milestone
            existing = old_milestones[ms.id]
            existing.name = ms.name
            existing.position = ms.position if ms.position is not None else i
            new_ids.add(ms.id)
        else:
            # Create new milestone
            db.add(ProjectMilestone(project_id=project_id, name=ms.name, position=ms.position if ms.position is not None else i))

    # Delete milestones that are no longer in the list
    for ms_id, ms in old_milestones.items():
        if ms_id not in new_ids:
            await db.delete(ms)

    await db.commit()
    return await _get_project_response(db, project_id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    if project_id == "proj_inbox":
        raise HTTPException(status_code=400, detail="Cannot delete the Inbox project")
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()


async def _get_project_response(db: AsyncSession, project_id: str) -> ProjectResponse | None:
    result = await db.execute(
        select(Project).where(Project.id == project_id).options(selectinload(Project.milestones))
    )
    project = result.scalar_one_or_none()
    if project is None:
        return None
    return await _project_to_response(db, project)


async def _project_to_response(db: AsyncSession, project: Project) -> ProjectResponse:
    # Get task count for this project
    count_result = await db.execute(
        select(func.count()).select_from(Task).where(Task.project_id == project.id)
    )
    task_count = count_result.scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        color=project.color,
        icon=getattr(project, "icon", None) or "folder-kanban",
        status=project.status or "active",
        position=getattr(project, "position", None) or 0,
        milestones=[
            {"id": ms.id, "name": ms.name, "position": ms.position}
            for ms in sorted(project.milestones, key=lambda m: m.position)
        ],
        task_count=task_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
