import uuid

import pytest
import pytest_asyncio

from app.models.task import TaskStatus
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test Project", path="/tmp/test", description="Test")


async def test_create_task(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Do something", priority=1)
    assert task.description == "Do something"
    assert task.priority == 1
    assert task.status == TaskStatus.NEW
    assert task.project_id == project.id


async def test_list_tasks_by_project(db_session, project):
    service = TaskService(db_session)
    await service.create(project_id=project.id, description="Task 1", priority=1)
    await service.create(project_id=project.id, description="Task 2", priority=2)
    tasks = await service.list_by_project(project.id)
    assert len(tasks) == 2


async def test_list_tasks_filter_status(db_session, project):
    service = TaskService(db_session)
    await service.create(project_id=project.id, description="New task", priority=1)
    tasks = await service.list_by_project(project.id, status=TaskStatus.NEW)
    assert len(tasks) == 1
    tasks = await service.list_by_project(project.id, status=TaskStatus.PLANNED)
    assert len(tasks) == 0


async def test_get_next_task_priority_order(db_session, project):
    service = TaskService(db_session)
    await service.create(project_id=project.id, description="Low priority", priority=5)
    await service.create(project_id=project.id, description="High priority", priority=1)
    task = await service.get_next_task(project.id)
    assert task is not None
    assert task.description == "High priority"


async def test_get_next_task_declined_before_new(db_session, project):
    service = TaskService(db_session)
    new_task = await service.create(project_id=project.id, description="New task", priority=1)
    declined_task = await service.create(project_id=project.id, description="Declined task", priority=5)
    declined_task.status = TaskStatus.DECLINED
    declined_task.decline_feedback = "Try again"
    await db_session.flush()

    task = await service.get_next_task(project.id)
    assert task.id == declined_task.id


async def test_get_next_task_none_available(db_session, project):
    service = TaskService(db_session)
    task = await service.get_next_task(project.id)
    assert task is None


async def test_update_status_valid_transition(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Plan me", priority=1)
    updated = await service.update_status(task.id, project.id, TaskStatus.PLANNED)
    assert updated.status == TaskStatus.PLANNED


async def test_update_status_invalid_transition(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Skip ahead", priority=1)
    with pytest.raises(ValueError, match="Invalid state transition"):
        await service.update_status(task.id, project.id, TaskStatus.FINISHED)


async def test_update_status_canceled_from_any(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Cancel me", priority=1)
    updated = await service.update_status(task.id, project.id, TaskStatus.CANCELED)
    assert updated.status == TaskStatus.CANCELED


async def test_update_status_declined_saves_feedback(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Decline me", priority=1)
    await service.update_status(task.id, project.id, TaskStatus.PLANNED)
    updated = await service.update_status(task.id, project.id, TaskStatus.DECLINED, decline_feedback="Not good enough")
    assert updated.status == TaskStatus.DECLINED
    assert updated.decline_feedback == "Not good enough"


async def test_set_task_name(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Name me", priority=1)
    updated = await service.set_name(task.id, project.id, "My Task Name")
    assert updated.name == "My Task Name"


async def test_save_plan(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Plan me", priority=1)
    updated = await service.save_plan(task.id, project.id, "# The Plan\n\nDo things.")
    assert updated.plan == "# The Plan\n\nDo things."
    assert updated.status == TaskStatus.PLANNED


async def test_save_plan_from_declined(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Replan me", priority=1)
    task.status = TaskStatus.DECLINED
    await db_session.flush()
    updated = await service.save_plan(task.id, project.id, "# New Plan")
    assert updated.status == TaskStatus.PLANNED


async def test_save_plan_invalid_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Already planned", priority=1)
    task.status = TaskStatus.ACCEPTED
    await db_session.flush()
    with pytest.raises(ValueError, match="Can only save plan"):
        await service.save_plan(task.id, project.id, "# Plan")


async def test_complete_task(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Finish me", priority=1)
    task.status = TaskStatus.ACCEPTED
    await db_session.flush()
    updated = await service.complete_task(task.id, project.id, "All done. Implemented X and Y.")
    assert updated.status == TaskStatus.FINISHED
    assert updated.recap == "All done. Implemented X and Y."


async def test_complete_task_invalid_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not ready", priority=1)
    with pytest.raises(ValueError, match="Can only complete"):
        await service.complete_task(task.id, project.id, "Done")


async def test_task_project_mismatch(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    other_project_id = uuid.uuid4()
    with pytest.raises(PermissionError, match="does not belong"):
        await service.set_name(task.id, other_project_id, "Name")


# ── create_spec ──────────────────────────────────────────────────────────────

async def test_create_spec_from_new(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Spec me", priority=1)
    updated = await service.create_spec(task.id, project.id, "# Spec\n\nDo X.")
    assert updated.specification == "# Spec\n\nDo X."
    assert updated.status == TaskStatus.REASONING


async def test_create_spec_from_declined(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Respec me", priority=1)
    task.status = TaskStatus.DECLINED
    await db_session.flush()
    updated = await service.create_spec(task.id, project.id, "# New Spec")
    assert updated.status == TaskStatus.REASONING


async def test_create_spec_invalid_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Already reasoning", priority=1)
    task.status = TaskStatus.REASONING
    await db_session.flush()
    with pytest.raises(ValueError, match="New or Declined"):
        await service.create_spec(task.id, project.id, "# Spec")


async def test_create_spec_blank_raises(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    with pytest.raises(ValueError, match="blank"):
        await service.create_spec(task.id, project.id, "   ")


# ── edit_spec ─────────────────────────────────────────────────────────────────

async def test_edit_spec(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Edit spec", priority=1)
    await service.create_spec(task.id, project.id, "# Original")
    updated = await service.edit_spec(task.id, project.id, "# Updated Spec")
    assert updated.specification == "# Updated Spec"
    assert updated.status == TaskStatus.REASONING


async def test_edit_spec_wrong_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not reasoning", priority=1)
    with pytest.raises(ValueError, match="Reasoning status"):
        await service.edit_spec(task.id, project.id, "# Spec")


async def test_edit_spec_blank_raises(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    task.status = TaskStatus.REASONING
    await db_session.flush()
    with pytest.raises(ValueError, match="blank"):
        await service.edit_spec(task.id, project.id, "")


# ── create_plan ───────────────────────────────────────────────────────────────

async def test_create_plan_from_reasoning(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Plan me", priority=1)
    await service.create_spec(task.id, project.id, "# Spec")
    updated = await service.create_plan(task.id, project.id, "# Plan\n\nStep 1.")
    assert updated.plan == "# Plan\n\nStep 1."
    assert updated.status == TaskStatus.PLANNED


async def test_create_plan_wrong_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not reasoned", priority=1)
    with pytest.raises(ValueError, match="Reasoning status"):
        await service.create_plan(task.id, project.id, "# Plan")


async def test_create_plan_blank_raises(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    task.status = TaskStatus.REASONING
    await db_session.flush()
    with pytest.raises(ValueError, match="blank"):
        await service.create_plan(task.id, project.id, "  ")


# ── edit_plan ─────────────────────────────────────────────────────────────────

async def test_edit_plan(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Edit plan", priority=1)
    await service.create_spec(task.id, project.id, "# Spec")
    await service.create_plan(task.id, project.id, "# Plan v1")
    updated = await service.edit_plan(task.id, project.id, "# Plan v2")
    assert updated.plan == "# Plan v2"
    assert updated.status == TaskStatus.PLANNED


async def test_edit_plan_wrong_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not planned", priority=1)
    with pytest.raises(ValueError, match="Planned status"):
        await service.edit_plan(task.id, project.id, "# Plan")


async def test_edit_plan_blank_raises(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Test", priority=1)
    task.status = TaskStatus.PLANNED
    await db_session.flush()
    with pytest.raises(ValueError, match="blank"):
        await service.edit_plan(task.id, project.id, "")


# ── accept_task ───────────────────────────────────────────────────────────────

async def test_accept_task(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Accept me", priority=1)
    task.status = TaskStatus.PLANNED
    await db_session.flush()
    updated = await service.accept_task(task.id, project.id)
    assert updated.status == TaskStatus.ACCEPTED


async def test_accept_task_wrong_status(db_session, project):
    service = TaskService(db_session)
    task = await service.create(project_id=project.id, description="Not planned", priority=1)
    with pytest.raises(ValueError, match="Planned status"):
        await service.accept_task(task.id, project.id)


# ── cancel_task ───────────────────────────────────────────────────────────────

async def test_cancel_task_from_any_status(db_session, project):
    service = TaskService(db_session)
    for status in [TaskStatus.NEW, TaskStatus.REASONING, TaskStatus.PLANNED, TaskStatus.ACCEPTED]:
        task = await service.create(project_id=project.id, description=f"Cancel from {status}", priority=1)
        task.status = status
        await db_session.flush()
        updated = await service.cancel_task(task.id, project.id)
        assert updated.status == TaskStatus.CANCELED
