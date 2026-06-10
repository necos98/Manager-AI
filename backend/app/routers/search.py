import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.search import SearchResultItem, SearchResults
from app.services.project_service import ProjectService
from app.storage import issue_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])

# Static page map: route path → human label
PAGE_MAP: list[tuple[str, str, str | None]] = [
    ("/", "Dashboard", None),
    ("/projects/new", "New Project", None),
    ("/projects/archived", "Archived Projects", None),
    ("/agents", "Agents", None),
    ("/pipelines", "Pipelines", None),
    ("/providers", "Providers", None),
    ("/questions", "Questions", None),
    ("/queue", "Queue", None),
    ("/settings", "Settings", None),
    ("/terminals", "Terminals", None),
    ("/library", "Library", None),
]


def _make_page_url(base: str, project_id: str | None = None) -> str:
    """Build a frontend route path from a template with optional project_id."""
    if project_id and "$projectId" in base:
        return base.replace("$projectId", project_id)
    return base


def _match_text(text: str | None, query: str) -> bool:
    """Case-insensitive substring match."""
    if not text:
        return False
    return query in text.lower()


@router.get("/search", response_model=SearchResults)
async def global_search(
    q: str = Query("", min_length=0, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across all projects, issues, and app pages.

    Returns results grouped by category: issues, projects, pages.
    Each result includes enough context to build a frontend link.
    """
    query = q.strip().lower()
    results = SearchResults()

    if not query:
        return results

    MAX_RESULTS = 20
    project_service = ProjectService(db)

    # ── Fetch all non-archived projects ──
    all_projects = await project_service.list_all(archived=False)
    project_map = {p.id: p for p in all_projects}

    # ── Issue search: iterate every project's issues ──
    for project in all_projects:
        try:
            records = issue_store.list_issues_full(project.path)
        except Exception:
            logger.warning("Failed to read issues for project %s (%s)", project.id, project.path, exc_info=True)
            continue
        for rec in records:
            if rec.project_id != project.id:
                continue
            if not _match_text(rec.name, query) and not _match_text(rec.description, query):
                continue
            results.issues.append(
                SearchResultItem(
                    id=rec.id,
                    name=rec.name or "Untitled",
                    description=rec.description[:200] if rec.description else "",
                    type="issue",
                    status=rec.status,
                    project_id=project.id,
                    project_name=project.name,
                    priority=rec.priority,
                    url=f"/projects/{project.id}/issues/{rec.id}",
                )
            )
            if len(results.issues) >= MAX_RESULTS:
                break
        if len(results.issues) >= MAX_RESULTS:
            break

    # ── Project search ──
    for project in all_projects:
        if len(results.projects) >= MAX_RESULTS:
            break
        if not _match_text(project.name, query) and not _match_text(project.description, query):
            continue
        results.projects.append(
            SearchResultItem(
                id=project.id,
                name=project.name,
                description=(project.description or "")[:200],
                type="project",
                status=None,
                project_id=project.id,
                project_name=project.name,
                priority=None,
                url=f"/projects/{project.id}/issues",
            )
        )

    # ── Page search ──
    for route_path, label, _ in PAGE_MAP:
        if len(results.pages) >= MAX_RESULTS:
            break
        if not _match_text(label, query) and not _match_text(route_path, query):
            continue
        results.pages.append(
            SearchResultItem(
                id=route_path,
                name=label,
                description=f"App page: {route_path}",
                type="page",
                status=None,
                project_id=None,
                project_name=None,
                priority=None,
                url=route_path,
            )
        )

    return results
