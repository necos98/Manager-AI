from pydantic import BaseModel
from typing import Optional


class SearchResultItem(BaseModel):
    id: str
    name: str
    description: str
    type: str  # "issue" | "project" | "page"
    status: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    priority: Optional[int] = None
    url: str  # Frontend route path


class SearchResults(BaseModel):
    issues: list[SearchResultItem] = []
    projects: list[SearchResultItem] = []
    pages: list[SearchResultItem] = []
