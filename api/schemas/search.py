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


class TaskSearchResultItem(BaseModel):
    id: str
    title: str
    description: str
    status: str
    project_id: str


class SearchResult(BaseModel):
    results: list[SearchResultItem]
    tasks: list[TaskSearchResultItem] = []
    total: int
    query: str
