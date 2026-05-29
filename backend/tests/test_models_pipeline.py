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
async def test_full_chain_insert(db_session):
    """Insert Agent → Pipeline → PipelineStep → PipelineRun → PipelineStepRun → PipelineMessage."""
    agent = Agent(id="a1", name="spec-writer", system_prompt="You write specs")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Default")
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
    agent = Agent(id="a1", name="dev", system_prompt="Dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
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
    agent = Agent(id="a1", name="dev", system_prompt="Dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
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
    agent = Agent(id="a1", name="dev", system_prompt="Dev")
    db_session.add(agent)
    await db_session.flush()

    pipeline = Pipeline(id="pl1", name="Test")
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
async def test_reorder_steps_no_constraint_violation(db_session):
<<<<<<< Updated upstream
    """Reorder that would trigger autoflush UNIQUE conflict succeeds with bulk UPDATE."""
=======
    """Reorder that would trigger autoflush UNIQUE conflict succeeds."""
>>>>>>> Stashed changes
    from app.services.pipeline_service import PipelineService

    agent = Agent(id="a1", name="dev", system_prompt="Dev")
    pipeline = Pipeline(id="pl1", name="Test")
    db_session.add_all([agent, pipeline])
    await db_session.flush()

    s1 = PipelineStep(id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0, terminal_command="echo 1")
    s2 = PipelineStep(id="ps2", pipeline_id="pl1", agent_id="a1", order_index=1, terminal_command="echo 2")
    s3 = PipelineStep(id="ps3", pipeline_id="pl1", agent_id="a1", order_index=2, terminal_command="echo 3")
    db_session.add_all([s1, s2, s3])
    await db_session.flush()

    svc = PipelineService(db_session)
    # Reverse order: was [0,1,2], becomes [2,1,0]
    steps = await svc.reorder_steps("pl1", ["ps3", "ps2", "ps1"])

    assert len(steps) == 3
    assert [s.id for s in steps] == ["ps3", "ps2", "ps1"]
    assert [s.order_index for s in steps] == [0, 1, 2]


@pytest.mark.asyncio
async def test_pipeline_step_run_status_enum_values():
    """Verify PipelineStepRunStatus enum members."""
    assert PipelineStepRunStatus.PENDING.value == "PENDING"
    assert PipelineStepRunStatus.RUNNING.value == "RUNNING"
    assert PipelineStepRunStatus.COMPLETED.value == "COMPLETED"
    assert PipelineStepRunStatus.FAILED.value == "FAILED"
