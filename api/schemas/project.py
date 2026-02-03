from datetime import datetime

from pydantic import BaseModel


class MilestoneCreate(BaseModel):
    id: str | None = None
    name: str
    position: int = 0


class MilestoneResponse(BaseModel):
    id: str
    name: str
    position: int

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    id: str  # proj_<name> format
    name: str
    description: str = ""
    color: str = "#6366f1"
    icon: str = "folder-kanban"
    milestones: list[MilestoneCreate] = []


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    icon: str | None = None
    status: str | None = None


class MilestoneUpdate(BaseModel):
    milestones: list[MilestoneCreate]


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    color: str
    icon: str = "folder-kanban"
    status: str = "active"
    milestones: list[MilestoneResponse]
    task_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectList(BaseModel):
    projects: list[ProjectResponse]
    total: int
