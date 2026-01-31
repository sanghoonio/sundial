from pydantic import BaseModel


class TagWithCount(BaseModel):
    name: str
    count: int


class TagListResponse(BaseModel):
    tags: list[TagWithCount]
