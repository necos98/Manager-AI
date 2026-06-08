import pytest
from sqlalchemy import select

from app.exceptions import ValidationError
from app.models.agent import Agent
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.services.pipeline_run import PipelineRunService


@pytest.fixture(autouse=True)
def _clear_step_completion_events():
    """Clear _step_completion_events between tests to avoid cross-test pollution."""
    from app.services.pipeline_run._completion import _completion_events
    _completion_events.clear()
    yield


def _make_agents(db_session, names):
    agents = {}
    for n in names:
        a = Agent(name=n)
        db_session.add(a)
        agents[n] = a
    return agents


async def _make_pipeline(db_session, agent_map, step_order):
    """Create a pipeline with steps in given order.

    step_order: list of (agent_name, order_index)
    Returns (pipeline, steps_dict)
    """
    pipeline = Pipeline(name="Test Pipeline")
    db_session.add(pipeline)
    await db_session.flush()

    steps = {}
    for agent_name, idx in step_order:
        s = PipelineStep(
            pipeline_id=pipeline.id,
            agent_id=agent_map[agent_name].id,
            order_index=idx,
        )
        db_session.add(s)
        steps[agent_name] = s
    await db_session.flush()
    return pipeline, steps


async def _make_run(
    db_session, pipeline, current_index, step_run_statuses
):
    """Create a run at a given step with specified step_run statuses.

    step_run_statuses: dict of step_id -> PipelineStepRunStatus
    """
    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id="iss-rej-1",
        status=PipelineRunStatus.RUNNING,
        current_step_index=current_index,
    )
    db_session.add(run)
    await db_session.flush()

    step_runs = {}
    for step_id, status in step_run_statuses.items():
        sr = PipelineStepRun(
            pipeline_run_id=run.id,
            pipeline_step_id=step_id,
            status=status,
        )
        db_session.add(sr)
        step_runs[step_id] = sr
    await db_session.flush()
    return run, step_runs


@pytest.mark.asyncio
async def test_reject_step_goes_backward(db_session):
    """Reject from CodeReviewer(step 2) -> Developer(step 1)."""
    agents = _make_agents(db_session, ["SpecWriter", "Developer", "CodeReviewer"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("SpecWriter", 0),
        ("Developer", 1),
        ("CodeReviewer", 2),
    ])
    run, srs = await _make_run(db_session, pipeline, 2, {
        steps["SpecWriter"].id: PipelineStepRunStatus.COMPLETED,
        steps["Developer"].id: PipelineStepRunStatus.COMPLETED,
        steps["CodeReviewer"].id: PipelineStepRunStatus.RUNNING,
    })

    svc = PipelineRunService(db_session)
    result = await svc.reject_step(
        run_id=run.id,
        reason="Quality gate failed: missing error handling",
        target_step_index=1,
        project_id="p1",
    )

    assert result["success"] is True
    assert result["rejection_count"] == 1
    assert result["max_reached"] is False

    await db_session.commit()

    # CodeReviewer step_run should now be REJECTED
    sr_reviewer = await db_session.get(PipelineStepRun, srs[steps["CodeReviewer"].id].id)
    assert sr_reviewer.status == PipelineStepRunStatus.REJECTED
    assert sr_reviewer.finished_at is not None

    # A new step_run should exist for Developer
    dev_step_runs = (
        await db_session.execute(
            select(PipelineStepRun).where(
                PipelineStepRun.pipeline_run_id == run.id,
                PipelineStepRun.pipeline_step_id == steps["Developer"].id,
            ).order_by(PipelineStepRun.started_at.desc().nulls_last())
        )
    ).scalars().all()
    assert len(dev_step_runs) == 2
    assert dev_step_runs[0].status == PipelineStepRunStatus.RUNNING

    # Run state updated
    run_check = await db_session.get(PipelineRun, run.id)
    assert run_check.current_step_index == 1
    assert run_check.rejection_count == 1
    assert run_check.status == PipelineRunStatus.RUNNING

    # Pipeline message created
    from app.models.pipeline_run import PipelineMessage
    msgs = (
        await db_session.execute(
            select(PipelineMessage).where(PipelineMessage.pipeline_run_id == run.id)
        )
    ).scalars().all()
    assert len(msgs) >= 1
    assert "rejected" in msgs[0].content.lower()
    assert "1" in msgs[0].content  # target step index in message


@pytest.mark.asyncio
async def test_reject_step_validates_target_not_forward(db_session):
    """Reject with target >= current step raises ValidationError."""
    agents = _make_agents(db_session, ["Dev", "Reviewer"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
        ("Reviewer", 1),
    ])
    run, srs = await _make_run(db_session, pipeline, 0, {
        steps["Dev"].id: PipelineStepRunStatus.RUNNING,
        steps["Reviewer"].id: PipelineStepRunStatus.PENDING,
    })

    svc = PipelineRunService(db_session)

    # Same index (reject to self) — should raise
    with pytest.raises(ValidationError, match="must be less than"):
        await svc.reject_step(
            run_id=run.id,
            reason="Self-reject not allowed",
            target_step_index=0,
            project_id="p1",
        )

    # Forward index — should raise
    with pytest.raises(ValidationError, match="must be less than"):
        await svc.reject_step(
            run_id=run.id,
            reason="Forward reject not allowed",
            target_step_index=1,
            project_id="p1",
        )

    # Negative index — should raise
    with pytest.raises(ValidationError, match=">= 0"):
        await svc.reject_step(
            run_id=run.id,
            reason="Negative index",
            target_step_index=-1,
            project_id="p1",
        )


@pytest.mark.asyncio
async def test_reject_step_out_of_bounds(db_session):
    """Reject with target_step_index beyond pipeline length."""
    agents = _make_agents(db_session, ["A", "B", "C"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("A", 0), ("B", 1), ("C", 2),
    ])
    run, srs = await _make_run(db_session, pipeline, 2, {
        steps["A"].id: PipelineStepRunStatus.COMPLETED,
        steps["B"].id: PipelineStepRunStatus.COMPLETED,
        steps["C"].id: PipelineStepRunStatus.RUNNING,
    })

    svc = PipelineRunService(db_session)
    with pytest.raises(ValidationError, match="out of bounds|less than"):
        await svc.reject_step(
            run_id=run.id,
            reason="Out of bounds",
            target_step_index=10,
            project_id="p1",
        )


@pytest.mark.asyncio
async def test_max_rejections_fails_pipeline(db_session):
    """3 rejections → pipeline FAILED."""
    agents = _make_agents(db_session, ["Dev", "Reviewer", "QA"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
        ("Reviewer", 1),
        ("QA", 2),
    ])
    run, srs = await _make_run(db_session, pipeline, 2, {
        steps["Dev"].id: PipelineStepRunStatus.COMPLETED,
        steps["Reviewer"].id: PipelineStepRunStatus.COMPLETED,
        steps["QA"].id: PipelineStepRunStatus.RUNNING,
    })

    svc = PipelineRunService(db_session)

    # Rejection 1: QA -> Reviewer
    r1 = await svc.reject_step(run.id, "Fix 1", 1, "p1")
    await db_session.commit()
    assert r1["rejection_count"] == 1
    assert r1["max_reached"] is False

    # Rejection 2: set QA RUNNING again, QA -> Reviewer (new step run)
    run.current_step_index = 2
    run.status = PipelineRunStatus.RUNNING
    qa_srs = (
        await db_session.execute(
            select(PipelineStepRun).where(
                PipelineStepRun.pipeline_run_id == run.id,
                PipelineStepRun.pipeline_step_id == steps["QA"].id,
            ).order_by(PipelineStepRun.started_at.desc().nulls_last())
        )
    ).scalars().all()
    qa_srs[0].status = PipelineStepRunStatus.RUNNING
    await db_session.flush()

    r2 = await svc.reject_step(run.id, "Fix 2", 1, "p1")
    await db_session.commit()
    assert r2["rejection_count"] == 2
    assert r2["max_reached"] is False

    # Rejection 3: set QA RUNNING again, QA -> Reviewer — max reached
    run.current_step_index = 2
    run.status = PipelineRunStatus.RUNNING
    qa_srs2 = (
        await db_session.execute(
            select(PipelineStepRun).where(
                PipelineStepRun.pipeline_run_id == run.id,
                PipelineStepRun.pipeline_step_id == steps["QA"].id,
            ).order_by(PipelineStepRun.started_at.desc().nulls_last())
        )
    ).scalars().all()
    qa_srs2[0].status = PipelineStepRunStatus.RUNNING
    await db_session.flush()

    r3 = await svc.reject_step(run.id, "Fix 3", 1, "p1")
    await db_session.commit()
    assert r3["rejection_count"] == 3
    assert r3["max_reached"] is True

    run_final = await db_session.get(PipelineRun, run.id)
    assert run_final.status == PipelineRunStatus.FAILED
    assert run_final.finished_at is not None


@pytest.mark.asyncio
async def test_rejection_creates_new_step_run(db_session):
    """Reject creates new RUNNING step_run on target, old stays REJECTED."""
    agents = _make_agents(db_session, ["Dev", "Reviewer"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
        ("Reviewer", 1),
    ])
    run, srs = await _make_run(db_session, pipeline, 1, {
        steps["Dev"].id: PipelineStepRunStatus.COMPLETED,
        steps["Reviewer"].id: PipelineStepRunStatus.RUNNING,
    })
    original_dev_sr_id = srs[steps["Dev"].id].id

    svc = PipelineRunService(db_session)
    await svc.reject_step(run.id, "Need changes", 0, "p1")
    await db_session.commit()

    # Original Dev step_run stays COMPLETED (not REJECTED — it wasn't RUNNING)
    orig = await db_session.get(PipelineStepRun, original_dev_sr_id)
    assert orig.status == PipelineStepRunStatus.COMPLETED

    # New Dev step_run created with RUNNING
    dev_srs = (
        await db_session.execute(
            select(PipelineStepRun).where(
                PipelineStepRun.pipeline_run_id == run.id,
                PipelineStepRun.pipeline_step_id == steps["Dev"].id,
            ).order_by(PipelineStepRun.started_at.desc().nulls_last())
        )
    ).scalars().all()
    assert len(dev_srs) == 2
    assert dev_srs[0].status == PipelineStepRunStatus.RUNNING

    # Reviewer stays REJECTED
    reviewer = await db_session.get(PipelineStepRun, srs[steps["Reviewer"].id].id)
    assert reviewer.status == PipelineStepRunStatus.REJECTED


@pytest.mark.asyncio
async def test_reject_non_running_pipeline_raises(db_session):
    """Reject on a non-RUNNING pipeline raises."""
    agents = _make_agents(db_session, ["Dev"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
    ])
    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id="iss-done",
        status=PipelineRunStatus.COMPLETED,
        current_step_index=0,
    )
    db_session.add(run)
    await db_session.flush()

    sr = PipelineStepRun(
        pipeline_run_id=run.id,
        pipeline_step_id=steps["Dev"].id,
        status=PipelineStepRunStatus.COMPLETED,
    )
    db_session.add(sr)
    await db_session.flush()

    svc = PipelineRunService(db_session)
    with pytest.raises(ValidationError, match="running"):
        await svc.reject_step(run.id, "Late reject", 0, "p1")


@pytest.mark.asyncio
async def test_set_step_completed_signals_event(db_session):
    """set_step_completed correctly signals the asyncio.Event for a step."""
    from app.services.pipeline_run import set_step_completed
    from app.services.pipeline_run._completion import _completion_events
    import asyncio

    evt = asyncio.Event()
    _completion_events[("run-1", 0)] = evt

    assert evt.is_set() is False
    result = set_step_completed("run-1", 0)
    assert result is True
    assert evt.is_set() is True

    # Non-existent key returns False
    result2 = set_step_completed("run-1", 99)
    assert result2 is False
