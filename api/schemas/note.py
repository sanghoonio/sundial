from datetime import datetime

from pydantic import BaseModel


class ChatMessageSchema(BaseModel):
    role: str
    content: str


class BlockSchema(BaseModel):
    id: str
    type: str  # "md" or "chat"
    content: str = ""
    messages: list[ChatMessageSchema] = []


class NoteCreate(BaseModel):
    title: str
    content: str = ""
    tags: list[str] = []
    project_id: str | None = None
    blocks: list[dict] | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    project_id: str | None = None
    blocks: list[dict] | None = None


class NoteResponse(BaseModel):
    id: str
    title: str
    filepath: str
    content: str
    blocks: list[BlockSchema] = []
    tags: list[str]
    project_id: str | None
    is_archived: bool = False
    linked_notes: list[str] = []
    linked_tasks: list[str] = []
    linked_events: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoteListItem(BaseModel):
    id: str
    title: str
    filepath: str
    tags: list[str]
    project_id: str | None
    linked_tasks: list[str] = []
    linked_events: list[str] = []
    preview: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoteList(BaseModel):
    notes: list[NoteListItem]
    total: int


class BacklinkItem(BaseModel):
    id: str
    title: str
    filepath: str


class BacklinkTaskItem(BaseModel):
    id: str
    title: str
    status: str


class BacklinksResponse(BaseModel):
    notes: list[BacklinkItem]
    tasks: list[BacklinkTaskItem]
