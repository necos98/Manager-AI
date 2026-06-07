import pytest
from sqlalchemy import select

from app.exceptions import NotFoundError
from app.models.agent import Agent
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_event_rule import PipelineEventRule
from app.models.pipeline_run import PipelineRun, PipelineRunStatus, PipelineStepRun, PipelineStepRunStatus
from app.services.pipeline_service import PipelineService
from app.services.pipeline_run_service import PipelineRunService


def _make_agents(db_session, names):
    agents = {}
    for n in names:
        a = Agent(name=n)
        db_session.add(a)
        agents[n] = a
    return agents


async def _make_pipeline(db_session, agent_map, step_order):
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


async def _make_run(db_session, pipeline, current_index, step_run_statuses):
    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id="iss-events-1",
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
async def test_add_and_list_event_rules(db_session):
    svc = PipelineService(db_session)
    agents = _make_agents(db_session, ["Dev", "Reviewer"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
        ("Reviewer", 1),
    ])

    rule = await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_rejected",
        source_step_id=steps["Reviewer"].id,
        target_step_id=steps["Dev"].id,
    )
    assert rule.event_type == "step_rejected"
    assert rule.source_step_id == steps["Reviewer"].id
    assert rule.target_step_id == steps["Dev"].id
    assert rule.enabled is True

    rules = await svc.list_event_rules(pipeline.id)
    assert len(rules) == 1
    assert rules[0].id == rule.id


@pytest.mark.asyncio
async def test_get_event_rule_for_step(db_session):
    svc = PipelineService(db_session)
    agents = _make_agents(db_session, ["Dev", "Reviewer", "QA"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
        ("Reviewer", 1),
        ("QA", 2),
    ])

    await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_rejected",
        source_step_id=steps["Reviewer"].id,
        target_step_id=steps["Dev"].id,
    )

    found = await svc.get_event_rule_for_step(
        pipeline.id, "step_rejected", steps["Reviewer"].id
    )
    assert found is not None
    assert found.target_step_id == steps["Dev"].id

    not_found = await svc.get_event_rule_for_step(
        pipeline.id, "step_rejected", steps["QA"].id
    )
    assert not_found is None


@pytest.mark.asyncio
async def test_remove_event_rule(db_session):
    svc = PipelineService(db_session)
    agents = _make_agents(db_session, ["Dev", "Reviewer"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
        ("Reviewer", 1),
    ])

    rule = await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_rejected",
        source_step_id=steps["Reviewer"].id,
        target_step_id=steps["Dev"].id,
    )
    await svc.remove_event_rule(rule.id)

    rules = await svc.list_event_rules(pipeline.id)
    assert len(rules) == 0


@pytest.mark.asyncio
async def test_add_event_rule_invalid_step_id(db_session):
    svc = PipelineService(db_session)
    agents = _make_agents(db_session, ["Dev"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
    ])

    with pytest.raises(NotFoundError):
        await svc.add_event_rule(
            pipeline_id=pipeline.id,
            event_type="step_rejected",
            source_step_id="non-existent",
            target_step_id="non-existent",
        )


@pytest.mark.asyncio
async def test_resolve_rejection_target(db_session):
    pipeline_svc = PipelineService(db_session)
    agents = _make_agents(db_session, ["SpecWriter", "Developer", "CodeReviewer"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("SpecWriter", 0),
        ("Developer", 1),
        ("CodeReviewer", 2),
    ])

    await pipeline_svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_rejected",
        source_step_id=steps["CodeReviewer"].id,
        target_step_id=steps["Developer"].id,
    )
    await db_session.commit()

    run, srs = await _make_run(db_session, pipeline, 2, {
        steps["SpecWriter"].id: PipelineStepRunStatus.COMPLETED,
        steps["Developer"].id: PipelineStepRunStatus.COMPLETED,
        steps["CodeReviewer"].id: PipelineStepRunStatus.RUNNING,
    })

    run_svc = PipelineRunService(db_session)
    target = await run_svc.resolve_rejection_target(run.id, steps["CodeReviewer"].id)
    assert target == 1


@pytest.mark.asyncio
async def test_resolve_rejection_target_no_rule(db_session):
    pipeline_svc = PipelineService(db_session)
    agents = _make_agents(db_session, ["Dev", "Reviewer"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
        ("Reviewer", 1),
    ])

    run, srs = await _make_run(db_session, pipeline, 1, {
        steps["Dev"].id: PipelineStepRunStatus.COMPLETED,
        steps["Reviewer"].id: PipelineStepRunStatus.RUNNING,
    })

    run_svc = PipelineRunService(db_session)
    target = await run_svc.resolve_rejection_target(run.id, steps["Reviewer"].id)
    assert target is None
