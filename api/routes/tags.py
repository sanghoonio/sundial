from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.note import NoteTag, Tag
from api.schemas.tag import TagListResponse, TagWithCount
from api.utils.auth import get_current_user

router = APIRouter(prefix="/tags", tags=["tags"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=TagListResponse)
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Tag.name, func.count(NoteTag.note_id).label("count"))
        .join(NoteTag, Tag.id == NoteTag.tag_id)
        .group_by(Tag.id)
        .order_by(func.count(NoteTag.note_id).desc())
    )
    rows = result.fetchall()
    return TagListResponse(
        tags=[TagWithCount(name=row[0], count=row[1]) for row in rows]
    )
