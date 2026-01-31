from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.schemas.search import SearchResult, SearchResultItem
from api.utils.auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=SearchResult)
async def search_notes(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # Use FTS5 for full-text search (standalone table, join on id)
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
    except Exception:
        # If FTS query fails (e.g., bad syntax), return empty
        return SearchResult(results=[], total=0, query=q)

    items = [
        SearchResultItem(
            id=row[0],
            title=row[1],
            filepath=row[2],
            snippet=row[3] or "",
            rank=float(row[4]),
        )
        for row in rows
    ]

    return SearchResult(results=items, total=total, query=q)
