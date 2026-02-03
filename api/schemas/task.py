from datetime import datetime

from pydantic import BaseModel


class ChecklistItemCreate(BaseModel):
    text: str
    is_checked: bool = False


class ChecklistItemResponse(BaseModel):
    id: str
    text: str
    is_checked: bool
    position: int

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    due_date: datetime | None = None
    project_id: str = "proj_inbox"
    milestone_id: str | None = None
    source_note_id: str | None = None
    calendar_event_id: str | None = None
    checklist: list[ChecklistItemCreate] = []
    note_ids: list[str] = []


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None
    project_id: str | None = None
    milestone_id: str | None = None
    checklist: list[ChecklistItemCreate] | None = None
    note_ids: list[str] | None = None


class TaskMove(BaseModel):
    milestone_id: str | None
    position: int = 0


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    priority: str
    due_date: datetime | None
    project_id: str
    milestone_id: str | None
    source_note_id: str | None = None
    calendar_event_id: str | None = None
    ai_suggested: bool = False
    position: int
    completed_at: datetime | None
    checklist: list[ChecklistItemResponse]
    note_ids: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskList(BaseModel):
    tasks: list[TaskResponse]
    total: int
