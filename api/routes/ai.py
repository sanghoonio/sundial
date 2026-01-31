from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.services.ai_service import ai_service
from api.utils.auth import get_current_user

router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(get_current_user)])


class ChatRequest(BaseModel):
    message: str
    note_id: str | None = None


class AIResponse(BaseModel):
    result: dict


class DailySuggestionsResponse(BaseModel):
    tasks: list = []
    notes: list = []


@router.post("/chat", response_model=AIResponse)
async def ai_chat(body: ChatRequest):
    result = await ai_service.chat(body.message, note_id=body.note_id)
    return AIResponse(result=result)


@router.post("/analyze-note/{note_id}", response_model=AIResponse)
async def analyze_note(note_id: str):
    result = await ai_service.analyze_note(note_id, content="")
    return AIResponse(result=result)


@router.get("/suggestions/daily", response_model=DailySuggestionsResponse)
async def daily_suggestions():
    """Stub: returns empty suggestions until AI is integrated."""
    return DailySuggestionsResponse(tasks=[], notes=[])
