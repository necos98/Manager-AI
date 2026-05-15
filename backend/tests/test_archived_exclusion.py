"""Tests that archived projects are excluded from cross-project scans."""

import pytest
import pytest_asyncio

from app.services.issue_service import IssueService
from app.services.memory_service import MemoryService
from app.services.task_service import TaskService
from app.services.project_service import ProjectService
from app.services.issue_relation_service import IssueRelationService


@pytest_asyncio.fixture
async def two_projects(db_session, tmp_path):
    """Create two projects. Returns (active, archived, project_svc)."""
    svc = ProjectService(db_session)
    active = await svc.create(name="Active", path=str(tmp_path / "active"))
    archived = await svc.create(name="Archived", path=str(tmp_path / "archived"))
    await db_session.flush()
    return active, archived, svc


# ---------------------------------------------------------------------------
# IssueService.get_by_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_issue_get_by_id_skips_archived(db_session, two_projects):
    active, archived, svc = two_projects

    # Create an issue in the to-be-archived project first
    issue_svc = IssueService(db_session)
    archived_issue = await issue_svc.create(project_id=archived.id, description="in archived")
    active_issue = await issue_svc.create(project_id=active.id, description="in active")

    # Archive it
    await svc.archive(archived.id)
    await db_session.flush()

    # get_by_id scans all non-archived projects — should NOT find the archived one
    found = await issue_svc.get_by_id(archived_issue.id)
    assert found is None

    # But listing by project directly still works (explicit project_id)
    issues = await issue_svc.list_by_project(archived.id)
    assert len(issues) == 1

    # Issue in active project is still findable
    found = await issue_svc.get_by_id(active_issue.id)
    assert found is not None
    assert found.description == "in active"


# ---------------------------------------------------------------------------
# TaskService cross-project scans
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_get_by_id_skips_archived(db_session, two_projects):
    active, archived, svc = two_projects

    issue_svc = IssueService(db_session)
    task_svc = TaskService(db_session)

    archived_issue = await issue_svc.create(project_id=archived.id, description="x")
    archived_tasks = await task_svc.create_bulk(archived_issue.id, [{"name": "Archived task"}])
    active_issue = await issue_svc.create(project_id=active.id, description="y")
    active_tasks = await task_svc.create_bulk(active_issue.id, [{"name": "Active task"}])

    await svc.archive(archived.id)
    await db_session.flush()

    from app.exceptions import NotFoundError
    with pytest.raises(NotFoundError):
        await task_svc.get_by_id(archived_tasks[0].id)

    found = await task_svc.get_by_id(active_tasks[0].id)
    assert found.name == "Active task"


@pytest.mark.asyncio
async def test_task_update_skips_archived(db_session, two_projects):
    active, archived, svc = two_projects

    issue_svc = IssueService(db_session)
    task_svc = TaskService(db_session)

    archived_issue = await issue_svc.create(project_id=archived.id, description="x")
    archived_tasks = await task_svc.create_bulk(archived_issue.id, [{"name": "Archived task"}])

    await svc.archive(archived.id)
    await db_session.flush()

    from app.exceptions import NotFoundError
    with pytest.raises(NotFoundError):
        await task_svc.update(archived_tasks[0].id, name="renamed")


@pytest.mark.asyncio
async def test_task_delete_skips_archived(db_session, two_projects):
    active, archived, svc = two_projects

    issue_svc = IssueService(db_session)
    task_svc = TaskService(db_session)

    archived_issue = await issue_svc.create(project_id=archived.id, description="x")
    archived_tasks = await task_svc.create_bulk(archived_issue.id, [{"name": "Archived task"}])

    await svc.archive(archived.id)
    await db_session.flush()

    from app.exceptions import NotFoundError
    with pytest.raises(NotFoundError):
        await task_svc.delete(archived_tasks[0].id)


# ---------------------------------------------------------------------------
# MemoryService._locate_memory
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_memory_locate_skips_archived(db_session, two_projects):
    active, archived, svc = two_projects

    mem_svc = MemoryService(db_session)
    mem = await mem_svc.create(project_id=archived.id, title="Archived mem", description="")

    await svc.archive(archived.id)
    await db_session.flush()

    from app.exceptions import AppError
    with pytest.raises(AppError):
        await mem_svc.get(mem.id)


# ---------------------------------------------------------------------------
# IssueRelationService._all_paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_relation_all_paths_skips_archived(db_session, two_projects):
    active, archived, svc = two_projects

    await svc.archive(archived.id)
    await db_session.flush()

    rel_svc = IssueRelationService(db_session)
    paths = await rel_svc._all_paths()

    assert active.path in paths
    assert archived.path not in paths


# ---------------------------------------------------------------------------
# Archived project items still accessible via direct project-scoped methods
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_archived_issues_still_listable_by_project(db_session, two_projects):
    active, archived, svc = two_projects

    issue_svc = IssueService(db_session)
    await issue_svc.create(project_id=archived.id, description="archived issue")
    await svc.archive(archived.id)
    await db_session.flush()

    # Direct project-scoped listing still works
    issues = await issue_svc.list_by_project(archived.id)
    assert len(issues) == 1


@pytest.mark.asyncio
async def test_unarchived_projects_findable_again(db_session, two_projects):
    active, archived, svc = two_projects

    issue_svc = IssueService(db_session)
    issue = await issue_svc.create(project_id=archived.id, description="x")

    await svc.archive(archived.id)
    await db_session.flush()

    # Not findable while archived
    found = await issue_svc.get_by_id(issue.id)
    assert found is None

    # Unarchive
    await svc.unarchive(archived.id)
    await db_session.flush()

    # Findable again
    found = await issue_svc.get_by_id(issue.id)
    assert found is not None
    assert found.description == "x"
