from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select

from app.exceptions import ValidationError
from app.models.agent import Agent
from app.models.issue import IssueStatus
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineMessage,
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.models.project import Project
from app.services.issue_service import IssueService
from app.services.pipeline_run_service import PipelineRunService
from app.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_start_creates_run_and_step_runs(db_session):
    agent = Agent(id="a1", name="dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
    step = PipelineStep(
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0
    )
    db_session.add_all([pipeline, step])
    await db_session.flush()

    svc = PipelineRunService(db_session)
    result = await svc.start(
        pipeline_id="pl1", issue_id="iss-1",
        project_id="p1", project_path="/tmp/p",
    )

    assert result["status"] == "RUNNING"
    assert result["issue_id"] == "iss-1"
    assert len(result["steps"]) == 1
    assert result["steps"][0]["agent_name"] == "dev"
    assert result["steps"][0]["status"] == "PENDING"

    run = (
        await db_session.execute(
            select(PipelineRun).where(PipelineRun.issue_id == "iss-1")
        )
    ).scalar_one_or_none()
    assert run is not None
    assert run.status == PipelineRunStatus.RUNNING

    step_runs = (
        await db_session.execute(
            select(PipelineStepRun).where(PipelineStepRun.pipeline_run_id == run.id)
        )
    ).scalars().all()
    assert len(step_runs) == 1
    assert step_runs[0].status == PipelineStepRunStatus.PENDING


@pytest.mark.asyncio
async def test_start_rejects_double_start(db_session):
    agent = Agent(id="a1", name="dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
    step = PipelineStep(
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0
    )
    db_session.add_all([pipeline, step])
    await db_session.flush()

    svc = PipelineRunService(db_session)
    await svc.start(
        pipeline_id="pl1", issue_id="iss-1",
        project_id="p1", project_path="/tmp/p",
    )

    with pytest.raises(ValidationError, match="already running"):
        await svc.start(
            pipeline_id="pl1", issue_id="iss-1",
            project_id="p1", project_path="/tmp/p",
        )


@pytest.mark.asyncio
async def test_get_run_returns_status(db_session):
    agent = Agent(id="a1", name="dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
    step = PipelineStep(
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0
    )
    db_session.add_all([pipeline, step])
    await db_session.flush()

    svc = PipelineRunService(db_session)
    started = await svc.start(
        pipeline_id="pl1", issue_id="iss-1",
        project_id="p1", project_path="/tmp/p",
    )

    result = await svc.get_run(started["id"])
    assert result["id"] == started["id"]
    assert result["status"] == "RUNNING"
    assert result["issue_id"] == "iss-1"
    assert len(result["steps"]) == 1
    assert result["steps"][0]["agent_name"] == "dev"


@pytest.mark.asyncio
async def test_add_and_get_messages(db_session):
    agent = Agent(id="a1", name="dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
    step = PipelineStep(
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0
    )
    db_session.add_all([pipeline, step])
    await db_session.flush()

    svc = PipelineRunService(db_session)
    started = await svc.start(
        pipeline_id="pl1", issue_id="iss-1",
        project_id="p1", project_path="/tmp/p",
    )

    msg = await svc.add_message(started["id"], "dev", "Hello from dev")
    assert msg["sender_agent_name"] == "dev"
    assert msg["content"] == "Hello from dev"
    assert msg["pipeline_run_id"] == started["id"]

    messages = await svc.get_messages(started["id"])
    assert len(messages) == 1
    assert messages[0]["content"] == "Hello from dev"


@pytest.mark.asyncio
async def test_cancel_run(db_session):
    agent = Agent(id="a1", name="dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
    step = PipelineStep(
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0
    )
    db_session.add_all([pipeline, step])
    await db_session.flush()

    svc = PipelineRunService(db_session)
    started = await svc.start(
        pipeline_id="pl1", issue_id="iss-1",
        project_id="p1", project_path="/tmp/p",
    )

    import asyncio
    await asyncio.sleep(0.1)

    result = await svc.cancel_run(started["id"])
    assert result is True

    run = await svc.get_run(started["id"])
    assert run["status"] == "FAILED"
    assert run["finished_at"] is not None


@pytest.mark.asyncio
async def test_cancel_non_running_raises(db_session):
    agent = Agent(id="a1", name="dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
    step = PipelineStep(
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0
    )
    db_session.add_all([pipeline, step])
    await db_session.flush()

    svc = PipelineRunService(db_session)
    started = await svc.start(
        pipeline_id="pl1", issue_id="iss-1",
        project_id="p1", project_path="/tmp/p",
    )
    # Manually mark run as FAILED so cancel raises ValidationError
    run = await db_session.get(PipelineRun, started["id"])
    run.status = PipelineRunStatus.FAILED
    await db_session.flush()

    with pytest.raises(ValidationError, match="only cancel active"):
        await svc.cancel_run(started["id"])


@pytest.mark.asyncio
async def test_get_runs_for_issue(db_session):
    agent = Agent(id="a1", name="dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
    step = PipelineStep(
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0
    )
    db_session.add_all([pipeline, step])
    await db_session.flush()

    svc = PipelineRunService(db_session)
    await svc.start(
        pipeline_id="pl1", issue_id="iss-1",
        project_id="p1", project_path="/tmp/p",
    )

    runs = await svc.get_runs_for_issue("iss-1")
    assert len(runs) == 1
    assert runs[0]["issue_id"] == "iss-1"

    empty = await svc.get_runs_for_issue("nonexistent")
    assert len(empty) == 0


@pytest.mark.asyncio
async def test_empty_pipeline_completes_immediately(db_session):
    pipeline = Pipeline(id="pl1", name="Empty")
    db_session.add(pipeline)
    await db_session.flush()

    svc = PipelineRunService(db_session)
    result = await svc.start(
        pipeline_id="pl1", issue_id="iss-1",
        project_id="p1", project_path="/tmp/p",
    )

    assert result["status"] == "RUNNING"
    assert len(result["steps"]) == 0


@pytest.mark.asyncio
async def test_finished_pipeline_step_accepts_accepted_issue(
    db_session, tmp_path, monkeypatch,
):
    """When no RUNNING pipeline run exists but issue is ACCEPTED,
    finished_pipeline_step should return success instead of error."""
    from app.mcp.server import finished_pipeline_step

    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="Test",
    )
    issue_svc = IssueService(db_session)
    issue = await issue_svc.create(
        project_id=project.id, description="Test issue", priority=1,
    )
    await issue_svc.create_spec(issue.id, project.id, "# Spec")
    await issue_svc.create_plan(issue.id, project.id, "## Plan")
    await issue_svc.accept_issue(issue.id, project.id)

    @asynccontextmanager
    async def mock_session():
        yield db_session

    monkeypatch.setattr("app.mcp.server.async_session", mock_session)

    result = await finished_pipeline_step(
        issue_id=issue.id, summary="Test completion",
    )

    assert result["success"] is True
    assert result["step_completed"] is True
    assert result["pipeline_finished"] is True
    assert "warning" in result


@pytest.mark.asyncio
async def test_finished_pipeline_step_errors_for_new_issue(
    db_session, tmp_path, monkeypatch,
):
    """When no RUNNING pipeline run exists and issue is NOT ACCEPTED,
    finished_pipeline_step should return error."""
    from app.mcp.server import finished_pipeline_step

    project = await ProjectService(db_session).create(
        name="Test", path=str(tmp_path), description="Test",
    )
    issue_svc = IssueService(db_session)
    issue = await issue_svc.create(
        project_id=project.id, description="Test issue", priority=1,
    )

    @asynccontextmanager
    async def mock_session():
        yield db_session

    monkeypatch.setattr("app.mcp.server.async_session", mock_session)

    result = await finished_pipeline_step(
        issue_id=issue.id, summary="Test completion",
    )

    assert "error" in result
    assert "No active pipeline run" in result["error"]
