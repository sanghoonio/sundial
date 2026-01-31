from pydantic import BaseModel


class SearchQuery(BaseModel):
    q: str
    limit: int = 20
    offset: int = 0


class SearchResultItem(BaseModel):
    id: str
    title: str
    filepath: str
    snippet: str
    rank: float


class SearchResult(BaseModel):
    results: list[SearchResultItem]
    total: int
    query: str
