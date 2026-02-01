from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.task import Task
from api.schemas.search import SearchResult, SearchResultItem, TaskSearchResultItem
from api.utils.auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=SearchResult)
async def search(
    q: str = Query(..., min_length=1),
    type: str = Query("all", description="Search type: notes, tasks, or all"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    note_items: list[SearchResultItem] = []
    task_items: list[TaskSearchResultItem] = []
    total = 0

    # Search notes via FTS5
    if type in ("all", "notes"):
        fts_query = text("""
            SELECT n.id, n.title, n.filepath, snippet(notes_fts, 2, '<mark>', '</mark>', '...', 32) as snippet, rank
            FROM notes_fts
            JOIN notes n ON notes_fts.id = n.id
            WHERE notes_fts MATCH :query
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """)
        count_query = text("""
            SELECT COUNT(*)
            FROM notes_fts
            WHERE notes_fts MATCH :query
        """)
        try:
            count_result = await db.execute(count_query, {"query": q})
            total = count_result.scalar() or 0
            result = await db.execute(fts_query, {"query": q, "limit": limit, "offset": offset})
            rows = result.fetchall()
            note_items = [
                SearchResultItem(
                    id=row[0], title=row[1], filepath=row[2],
                    snippet=row[3] or "", rank=float(row[4]),
                )
                for row in rows
            ]
        except Exception:
            pass

    # Search tasks via LIKE on title/description
    if type in ("all", "tasks"):
        pattern = f"%{q}%"
        task_query = (
            select(Task)
            .where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
            .order_by(Task.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        task_count_query = (
            select(func.count())
            .select_from(Task)
            .where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
        )
        try:
            task_count_result = await db.execute(task_count_query)
            task_total = task_count_result.scalar() or 0
            total += task_total
            task_result = await db.execute(task_query)
            task_items = [
                TaskSearchResultItem(
                    id=t.id, title=t.title, description=t.description or "",
                    status=t.status, project_id=t.project_id,
                )
                for t in task_result.scalars().all()
            ]
        except Exception:
            pass

    return SearchResult(results=note_items, tasks=task_items, total=total, query=q)
