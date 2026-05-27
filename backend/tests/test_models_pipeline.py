import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.agent import Agent
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineMessage,
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.models.project import Project


@pytest.mark.asyncio
async def test_all_tables_exist(db_session):
    """Verify all 6 pipeline tables are created."""
    rows = (await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    )).scalars().all()

    expected = {
        "agents", "pipelines", "pipeline_steps",
        "pipeline_runs", "pipeline_step_runs", "pipeline_messages",
    }
    missing = expected - set(rows)
    assert not missing, f"Missing tables: {missing}"


@pytest.mark.asyncio
async def test_agent_unique_constraint(db_session):
    """Duplicate agent name in same project raises IntegrityError."""
    project = Project(id="p1", name="P", path="/tmp/p")
    db_session.add(project)
    await db_session.flush()

    a1 = Agent(id="a1", project_id="p1", name="dev", system_prompt="You are a dev")
    a2 = Agent(id="a2", project_id="p1", name="dev", system_prompt="Duplicate")
    db_session.add_all([a1, a2])

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_agent_unique_name_across_projects(db_session):
    """Same agent name in different projects is allowed."""
    p1 = Project(id="p1", name="P1", path="/tmp/p1")
    p2 = Project(id="p2", name="P2", path="/tmp/p2")
    db_session.add_all([p1, p2])
    await db_session.flush()

    a1 = Agent(id="a1", project_id="p1", name="dev", system_prompt="Dev agent")
    a2 = Agent(id="a2", project_id="p2", name="dev", system_prompt="Dev agent")
    db_session.add_all([a1, a2])
    await db_session.flush()

    rows = (await db_session.execute(select(Agent).order_by(Agent.id))).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_full_chain_insert(db_session):
    """Insert Agent → Pipeline → PipelineStep → PipelineRun → PipelineStepRun → PipelineMessage."""
    project = Project(id="p1", name="P", path="/tmp/p")
    db_session.add(project)
    await db_session.flush()

    agent = Agent(id="a1", project_id="p1", name="spec-writer", system_prompt="You write specs")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", project_id="p1", name="Default")
    db_session.add(pipeline)
    await db_session.flush()

    step = PipelineStep(
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0,
        terminal_command='claude -p "write spec"',
    )
    db_session.add(step)
    await db_session.flush()

    run = PipelineRun(id="pr1", pipeline_id="pl1", issue_id="iss-1")
    db_session.add(run)
    await db_session.flush()

    step_run = PipelineStepRun(
        id="psr1", pipeline_run_id="pr1", pipeline_step_id="ps1",
    )
    db_session.add(step_run)
    await db_session.flush()

    msg = PipelineMessage(
        id="m1", pipeline_run_id="pr1", sender_agent_name="spec-writer",
        content="## Spec ready",
    )
    db_session.add(msg)
    await db_session.flush()

    # Verify
    assert (await db_session.execute(select(Agent))).scalars().first().name == "spec-writer"
    assert (await db_session.execute(select(Pipeline))).scalars().first().name == "Default"
    assert (await db_session.execute(select(PipelineRun))).scalars().first().status == PipelineRunStatus.RUNNING
    assert (await db_session.execute(select(PipelineStepRun))).scalars().first().status == PipelineStepRunStatus.PENDING
    assert (await db_session.execute(select(PipelineMessage))).scalars().first().sender_agent_name == "spec-writer"


@pytest.mark.asyncio
async def test_pipeline_cascade_deletes_steps(db_session):
    """Deleting a pipeline cascades to its steps."""
    project = Project(id="p1", name="P", path="/tmp/p")
    agent = Agent(id="a1", project_id="p1", name="dev", system_prompt="Dev")
    db_session.add_all([project, agent])
    await db_session.flush()

    pipeline = Pipeline(id="pl1", project_id="p1", name="Test")
    db_session.add(pipeline)
    await db_session.flush()

    step = PipelineStep(id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0, terminal_command="echo hi")
    db_session.add(step)
    await db_session.flush()

    assert (await db_session.execute(select(PipelineStep))).scalars().first() is not None

    await db_session.delete(pipeline)
    await db_session.flush()

    assert (await db_session.execute(select(PipelineStep))).scalars().first() is None


@pytest.mark.asyncio
async def test_pipeline_run_cascade_deletes_step_runs_and_messages(db_session):
    """Deleting a PipelineRun cascades to step_runs and messages."""
    project = Project(id="p1", name="P", path="/tmp/p")
    agent = Agent(id="a1", project_id="p1", name="dev", system_prompt="Dev")
    db_session.add_all([project, agent])
    await db_session.flush()

    pipeline = Pipeline(id="pl1", project_id="p1", name="Test")
    step = PipelineStep(id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0, terminal_command="echo hi")
    db_session.add_all([pipeline, step])
    await db_session.flush()

    run = PipelineRun(id="pr1", pipeline_id="pl1", issue_id="iss-1")
    db_session.add(run)
    await db_session.flush()

    step_run = PipelineStepRun(id="psr1", pipeline_run_id="pr1", pipeline_step_id="ps1")
    msg = PipelineMessage(id="m1", pipeline_run_id="pr1", sender_agent_name="dev", content="msg")
    db_session.add_all([step_run, msg])
    await db_session.flush()

    assert (await db_session.execute(select(PipelineStepRun))).scalars().first() is not None
    assert (await db_session.execute(select(PipelineMessage))).scalars().first() is not None

    await db_session.delete(run)
    await db_session.flush()

    assert (await db_session.execute(select(PipelineStepRun))).scalars().first() is None
    assert (await db_session.execute(select(PipelineMessage))).scalars().first() is None


@pytest.mark.asyncio
async def test_pipeline_step_unique_order_constraint(db_session):
    """Duplicate order_index in same pipeline raises IntegrityError."""
    project = Project(id="p1", name="P", path="/tmp/p")
    agent = Agent(id="a1", project_id="p1", name="dev", system_prompt="Dev")
    db_session.add_all([project, agent])
    await db_session.flush()

    pipeline = Pipeline(id="pl1", project_id="p1", name="Test")
    db_session.add(pipeline)
    await db_session.flush()

    s1 = PipelineStep(id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0, terminal_command="echo 1")
    s2 = PipelineStep(id="ps2", pipeline_id="pl1", agent_id="a1", order_index=0, terminal_command="echo 2")
    db_session.add_all([s1, s2])

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_pipeline_run_status_enum_values():
    """Verify PipelineRunStatus enum members."""
    assert PipelineRunStatus.RUNNING.value == "RUNNING"
    assert PipelineRunStatus.COMPLETED.value == "COMPLETED"
    assert PipelineRunStatus.FAILED.value == "FAILED"


@pytest.mark.asyncio
async def test_pipeline_step_run_status_enum_values():
    """Verify PipelineStepRunStatus enum members."""
    assert PipelineStepRunStatus.PENDING.value == "PENDING"
    assert PipelineStepRunStatus.RUNNING.value == "RUNNING"
    assert PipelineStepRunStatus.COMPLETED.value == "COMPLETED"
    assert PipelineStepRunStatus.FAILED.value == "FAILED"


@pytest.mark.asyncio
async def test_project_cascade_deletes_agents(db_session):
    """Deleting a project cascades to its agents."""
    project = Project(id="p1", name="P", path="/tmp/p")
    db_session.add(project)
    await db_session.flush()

    agent = Agent(id="a1", project_id="p1", name="dev", system_prompt="Dev")
    db_session.add(agent)
    await db_session.flush()

    assert (await db_session.execute(select(Agent))).scalars().first() is not None

    await db_session.delete(project)
    await db_session.flush()

    assert (await db_session.execute(select(Agent))).scalars().first() is None
