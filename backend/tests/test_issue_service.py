import uuid

import pytest
import pytest_asyncio

from app.exceptions import InvalidTransitionError, NotFoundError, ValidationError
from app.models.issue import IssueStatus
from app.services.project_service import ProjectService
from app.services.issue_service import IssueService
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test Project", path="/tmp/test", description="Test")


async def test_create_issue(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Do something", priority=1)
    assert issue.description == "Do something"
    assert issue.priority == 1
    assert issue.status == IssueStatus.NEW
    assert issue.project_id == project.id


async def test_list_issues_by_project(db_session, project):
    service = IssueService(db_session)
    await service.create(project_id=project.id, description="Issue 1", priority=1)
    await service.create(project_id=project.id, description="Issue 2", priority=2)
    issues = await service.list_by_project(project.id)
    assert len(issues) == 2


async def test_list_issues_filter_status(db_session, project):
    service = IssueService(db_session)
    await service.create(project_id=project.id, description="New issue", priority=1)
    issues = await service.list_by_project(project.id, status=IssueStatus.NEW)
    assert len(issues) == 1
    issues = await service.list_by_project(project.id, status=IssueStatus.PLANNED)
    assert len(issues) == 0


async def test_get_next_issue_priority_order(db_session, project):
    service = IssueService(db_session)
    await service.create(project_id=project.id, description="Low priority", priority=5)
    await service.create(project_id=project.id, description="High priority", priority=1)
    issue = await service.get_next_issue(project.id)
    assert issue is not None
    assert issue.description == "High priority"


async def test_get_next_issue_none_available(db_session, project):
    service = IssueService(db_session)
    issue = await service.get_next_issue(project.id)
    assert issue is None


async def test_update_status_valid_transition(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Plan me", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    updated = await service.update_status(issue.id, project.id, IssueStatus.PLANNED)
    assert updated.status == IssueStatus.PLANNED


async def test_update_status_invalid_transition(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Skip ahead", priority=1)
    with pytest.raises(InvalidTransitionError, match="Invalid state transition"):
        await service.update_status(issue.id, project.id, IssueStatus.FINISHED)


async def test_update_status_canceled_from_any(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Cancel me", priority=1)
    updated = await service.update_status(issue.id, project.id, IssueStatus.CANCELED)
    assert updated.status == IssueStatus.CANCELED


async def test_set_issue_name(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Name me", priority=1)
    updated = await service.set_name(issue.id, project.id, "My Issue Name")
    assert updated.name == "My Issue Name"


async def test_set_name_too_long_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Test", priority=1)
    long_name = "x" * 501
    with pytest.raises(ValidationError, match="500"):
        await service.set_name(issue.id, project.id, long_name)


async def test_complete_issue(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Finish me", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    updated = await service.complete_issue(issue.id, project.id, "All done. Implemented X and Y.")
    assert updated.status == IssueStatus.FINISHED
    assert updated.recap == "All done. Implemented X and Y."


async def test_complete_issue_invalid_status(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Not ready", priority=1)
    with pytest.raises(InvalidTransitionError, match="Can only complete"):
        await service.complete_issue(issue.id, project.id, "Done")


async def test_complete_issue_with_pending_tasks_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Has tasks", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    # Add pending tasks
    task_service = TaskService(db_session)
    await task_service.create_bulk(issue.id, [{"name": "Task 1"}, {"name": "Task 2"}])
    with pytest.raises(ValidationError, match="tasks not finished"):
        await service.complete_issue(issue.id, project.id, "Done")


async def test_complete_issue_with_all_tasks_completed(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Tasks done", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    # Add and complete tasks
    task_service = TaskService(db_session)
    tasks = await task_service.create_bulk(issue.id, [{"name": "Task 1"}])
    await task_service.update(tasks[0].id, status="In Progress")
    await task_service.update(tasks[0].id, status="Completed")
    updated = await service.complete_issue(issue.id, project.id, "All done")
    assert updated.status == IssueStatus.FINISHED


async def test_complete_issue_without_tasks_allowed(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="No tasks", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    updated = await service.complete_issue(issue.id, project.id, "Done without tasks")
    assert updated.status == IssueStatus.FINISHED


async def test_complete_issue_blank_recap_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Blank recap", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    with pytest.raises(ValidationError, match="blank"):
        await service.complete_issue(issue.id, project.id, "   ")


async def test_issue_project_mismatch(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Test", priority=1)
    other_project_id = uuid.uuid4()
    with pytest.raises(NotFoundError, match="not found"):
        await service.set_name(issue.id, other_project_id, "Name")


# -- create_spec ---------------------------------------------------------------

async def test_create_spec_from_new(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Spec me", priority=1)
    updated = await service.create_spec(issue.id, project.id, "# Spec\n\nDo X.")
    assert updated.specification == "# Spec\n\nDo X."
    assert updated.status == IssueStatus.REASONING


async def test_create_spec_invalid_status(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Already reasoning", priority=1)
    issue.status = IssueStatus.REASONING
    await db_session.flush()
    with pytest.raises(InvalidTransitionError, match="New"):
        await service.create_spec(issue.id, project.id, "# Spec")


async def test_create_spec_blank_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Test", priority=1)
    with pytest.raises(ValidationError, match="blank"):
        await service.create_spec(issue.id, project.id, "   ")


# -- edit_spec -----------------------------------------------------------------

async def test_edit_spec(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Edit spec", priority=1)
    await service.create_spec(issue.id, project.id, "# Original")
    updated = await service.edit_spec(issue.id, project.id, "# Updated Spec")
    assert updated.specification == "# Updated Spec"
    assert updated.status == IssueStatus.REASONING


async def test_edit_spec_wrong_status(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Not reasoning", priority=1)
    with pytest.raises(InvalidTransitionError, match="Reasoning"):
        await service.edit_spec(issue.id, project.id, "# Spec")


async def test_edit_spec_blank_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Test", priority=1)
    issue.status = IssueStatus.REASONING
    await db_session.flush()
    with pytest.raises(ValidationError, match="blank"):
        await service.edit_spec(issue.id, project.id, "")


# -- create_plan ---------------------------------------------------------------

async def test_create_plan_from_reasoning(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Plan me", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    updated = await service.create_plan(issue.id, project.id, "# Plan\n\nStep 1.")
    assert updated.plan == "# Plan\n\nStep 1."
    assert updated.status == IssueStatus.PLANNED


async def test_create_plan_wrong_status(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Not reasoned", priority=1)
    with pytest.raises(InvalidTransitionError, match="Reasoning"):
        await service.create_plan(issue.id, project.id, "# Plan")


async def test_create_plan_blank_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Test", priority=1)
    issue.status = IssueStatus.REASONING
    await db_session.flush()
    with pytest.raises(ValidationError, match="blank"):
        await service.create_plan(issue.id, project.id, "  ")


# -- edit_plan -----------------------------------------------------------------

async def test_edit_plan(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Edit plan", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan v1")
    updated = await service.edit_plan(issue.id, project.id, "# Plan v2")
    assert updated.plan == "# Plan v2"
    assert updated.status == IssueStatus.PLANNED


async def test_edit_plan_wrong_status(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Not planned", priority=1)
    with pytest.raises(InvalidTransitionError, match="Planned"):
        await service.edit_plan(issue.id, project.id, "# Plan")


async def test_edit_plan_blank_raises(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Test", priority=1)
    issue.status = IssueStatus.PLANNED
    await db_session.flush()
    with pytest.raises(ValidationError, match="blank"):
        await service.edit_plan(issue.id, project.id, "")


# -- accept_issue --------------------------------------------------------------

async def test_accept_issue(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Accept me", priority=1)
    issue.status = IssueStatus.PLANNED
    await db_session.flush()
    updated = await service.accept_issue(issue.id, project.id)
    assert updated.status == IssueStatus.ACCEPTED


async def test_accept_issue_wrong_status(db_session, project):
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Not planned", priority=1)
    with pytest.raises(InvalidTransitionError, match="Planned"):
        await service.accept_issue(issue.id, project.id)


# -- cancel_issue --------------------------------------------------------------

async def test_cancel_issue_from_any_status(db_session, project):
    service = IssueService(db_session)
    for status in [IssueStatus.NEW, IssueStatus.REASONING, IssueStatus.PLANNED, IssueStatus.ACCEPTED]:
        issue = await service.create(project_id=project.id, description=f"Cancel from {status}", priority=1)
        issue.status = status
        await db_session.flush()
        updated = await service.cancel_issue(issue.id, project.id)
        assert updated.status == IssueStatus.CANCELED


from app.services.activity_service import ActivityService


async def test_create_spec_logs_activity(db_session, project):
    svc = IssueService(db_session)
    activity_svc = ActivityService(db_session)
    issue = await svc.create(project_id=project.id, description="Log test", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")
    logs = await activity_svc.list_for_project(project.id, issue_id=issue.id)
    assert any(log.event_type == "spec_created" for log in logs)


async def test_create_plan_logs_activity(db_session, project):
    svc = IssueService(db_session)
    activity_svc = ActivityService(db_session)
    issue = await svc.create(project_id=project.id, description="Plan log test", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")
    await svc.create_plan(issue.id, project.id, "# Plan")
    logs = await activity_svc.list_for_project(project.id, issue_id=issue.id)
    assert any(log.event_type == "plan_created" for log in logs)


async def test_complete_issue_logs_activity(db_session, project):
    svc = IssueService(db_session)
    activity_svc = ActivityService(db_session)
    issue = await svc.create(project_id=project.id, description="Complete log test", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")
    await svc.create_plan(issue.id, project.id, "# Plan")
    await svc.accept_issue(issue.id, project.id)
    await svc.complete_issue(issue.id, project.id, "Done")
    logs = await activity_svc.list_for_project(project.id, issue_id=issue.id)
    assert any(log.event_type == "issue_completed" for log in logs)


async def test_complete_issue_blocks_when_lock_held(db_session, project):
    """complete_issue acquisisce un lock per-issue che blocca chiamate concorrenti."""
    import asyncio
    from app.services.issue_service import _issue_completion_locks

    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Concurrent test", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)

    # Pre-acquisire il lock per simulare una chiamata già in corso
    lock = asyncio.Lock()
    _issue_completion_locks[issue.id] = lock
    await lock.acquire()

    # complete_issue deve bloccarsi finché il lock è held
    task = asyncio.create_task(
        service.complete_issue(issue.id, project.id, "Done")
    )
    await asyncio.sleep(0.02)
    assert not task.done(), "complete_issue deve aspettare il lock"

    # Rilascio lock → complete_issue deve completare
    lock.release()
    result = await asyncio.wait_for(task, timeout=2.0)
    assert result.status == IssueStatus.FINISHED

    # Pulizia
    _issue_completion_locks.pop(issue.id, None)


async def test_complete_issue_concurrent_two_tasks(db_session, project):
    """Due chiamate concorrenti: la prima completa, la seconda riceve InvalidTransitionError."""
    import asyncio
    from app.exceptions import InvalidTransitionError

    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Concurrent complete", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)

    successes = []
    failures = []

    async def try_complete():
        try:
            result = await service.complete_issue(issue.id, project.id, "Done")
            successes.append(result)
        except InvalidTransitionError as e:
            failures.append(e)

    await asyncio.gather(try_complete(), try_complete())

    assert len(successes) == 1, "Esattamente una chiamata deve completare con successo"
    assert successes[0].status == IssueStatus.FINISHED
    assert len(failures) == 1, "La seconda chiamata deve ricevere InvalidTransitionError"
