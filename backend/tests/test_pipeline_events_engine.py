"""Tests for the pipeline event engine (_events_engine.py + fire_pipeline_event)."""

import pytest
from sqlalchemy import select

from app.models.agent import Agent
from app.models.issue import Issue, IssueStatus
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.models.project import Project
from app.services.pipeline_service import PipelineService
from app.services.pipeline_run import PipelineRunService, fire_pipeline_event


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


async def _make_project_and_issue(db_session):
    project = Project(name="Test Project", path="/tmp/test-project")
    db_session.add(project)
    await db_session.flush()
    issue = Issue(
        project_id=project.id,
        description="Test issue for event engine",
        status=IssueStatus.NEW,
    )
    db_session.add(issue)
    await db_session.flush()
    return project, issue


@pytest.mark.asyncio
async def test_fire_event_set_issue_status(db_session):
    """step_completed event with set_issue_status action changes issue status."""
    agents = _make_agents(db_session, ["SpecWriter", "Developer"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("SpecWriter", 0),
        ("Developer", 1),
    ])

    project, issue = await _make_project_and_issue(db_session)

    # Create the pipeline run (step 0 pending)
    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        status=PipelineRunStatus.RUNNING,
        current_step_index=0,
    )
    db_session.add(run)
    await db_session.flush()

    sr = PipelineStepRun(
        pipeline_run_id=run.id,
        pipeline_step_id=steps["SpecWriter"].id,
        status=PipelineStepRunStatus.COMPLETED,
    )
    db_session.add(sr)
    await db_session.flush()

    # Add event rule: step_completed from SpecWriter -> set issue to PLANNED
    svc = PipelineService(db_session)
    await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_completed",
        source_step_id=steps["SpecWriter"].id,
        target_step_id=steps["SpecWriter"].id,
        action_type="set_issue_status",
        action_params={"status": "PLANNED"},
    )
    await db_session.commit()

    # Fire event
    results = await fire_pipeline_event(
        pipeline_id=pipeline.id,
        event_type="step_completed",
        source_step_id=steps["SpecWriter"].id,
        run_id=run.id,
        issue_id=issue.id,
        project_id=project.id,
        agent_name="SpecWriter",
        step_run_id=sr.id,
        step_index=0,
        metadata={"event_type": "step_completed"},
        session=db_session,
    )

    assert len(results) == 1
    assert results[0]["status"] == "executed"

    # Verify issue status changed
    await db_session.refresh(issue)
    assert issue.status == IssueStatus.PLANNED


@pytest.mark.asyncio
async def test_fire_event_pipeline_completed_set_finished(db_session):
    """pipeline_completed event with set_issue_status=FINISHED."""
    agents = _make_agents(db_session, ["Tester"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Tester", 0),
    ])

    project, issue = await _make_project_and_issue(db_session)
    issue.status = IssueStatus.ACCEPTED
    db_session.add(issue)
    await db_session.flush()

    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        status=PipelineRunStatus.RUNNING,
        current_step_index=0,
    )
    db_session.add(run)
    await db_session.flush()

    # Add event rule: pipeline_completed -> set issue FINISHED
    svc = PipelineService(db_session)
    await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="pipeline_completed",
        source_step_id=steps["Tester"].id,
        target_step_id=steps["Tester"].id,
        action_type="set_issue_status",
        action_params={"status": "FINISHED", "recap_from": "summary"},
    )
    await db_session.commit()

    results = await fire_pipeline_event(
        pipeline_id=pipeline.id,
        event_type="pipeline_completed",
        source_step_id=None,  # pipeline-level event
        run_id=run.id,
        issue_id=issue.id,
        project_id=project.id,
        metadata={"status": "COMPLETED", "summary": "Pipeline finished successfully"},
        session=db_session,
    )

    assert len(results) == 1
    assert results[0]["status"] == "executed"

    await db_session.refresh(issue)
    assert issue.status == IssueStatus.FINISHED
    assert issue.recap == "Pipeline finished successfully"
    assert issue.finished_at is not None


@pytest.mark.asyncio
async def test_fire_event_no_matching_rule(db_session):
    """Firing an event with no matching rule returns empty list."""
    agents = _make_agents(db_session, ["Dev"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
    ])

    project, issue = await _make_project_and_issue(db_session)
    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        status=PipelineRunStatus.RUNNING,
        current_step_index=0,
    )
    db_session.add(run)
    await db_session.flush()

    # No rules added — should return empty
    results = await fire_pipeline_event(
        pipeline_id=pipeline.id,
        event_type="step_completed",
        source_step_id=steps["Dev"].id,
        run_id=run.id,
        issue_id=issue.id,
        project_id=project.id,
        session=db_session,
    )
    assert results == []


@pytest.mark.asyncio
async def test_fire_event_disabled_rule_skipped(db_session):
    """Disabled rules are not executed."""
    agents = _make_agents(db_session, ["Dev"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
    ])

    project, issue = await _make_project_and_issue(db_session)
    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        status=PipelineRunStatus.RUNNING,
        current_step_index=0,
    )
    db_session.add(run)
    await db_session.flush()

    svc = PipelineService(db_session)
    rule = await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_completed",
        source_step_id=steps["Dev"].id,
        target_step_id=steps["Dev"].id,
        action_type="set_issue_status",
        action_params={"status": "PLANNED"},
    )
    # Disable the rule
    rule.enabled = False
    db_session.add(rule)
    await db_session.commit()

    results = await fire_pipeline_event(
        pipeline_id=pipeline.id,
        event_type="step_completed",
        source_step_id=steps["Dev"].id,
        run_id=run.id,
        issue_id=issue.id,
        project_id=project.id,
        session=db_session,
    )
    assert results == []

    await db_session.refresh(issue)
    assert issue.status == IssueStatus.NEW


@pytest.mark.asyncio
async def test_fire_event_pipeline_level_source_step_none(db_session):
    """Pipeline-level event (source_step_id=None) matches rules regardless of source_step_id."""
    agents = _make_agents(db_session, ["Dev", "QA"])
    pipeline, steps = await _make_pipeline(db_session, agents, [
        ("Dev", 0),
        ("QA", 1),
    ])

    project, issue = await _make_project_and_issue(db_session)
    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        status=PipelineRunStatus.RUNNING,
        current_step_index=1,
    )
    db_session.add(run)
    await db_session.flush()

    svc = PipelineService(db_session)
    # Rule on QA step for pipeline_completed
    await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="pipeline_completed",
        source_step_id=steps["QA"].id,
        target_step_id=steps["QA"].id,
        action_type="set_issue_status",
        action_params={"status": "FINISHED"},
    )
    await db_session.commit()

    # Fire with source_step_id=None (pipeline-level event) — should match
    results = await fire_pipeline_event(
        pipeline_id=pipeline.id,
        event_type="pipeline_completed",
        source_step_id=None,
        run_id=run.id,
        issue_id=issue.id,
        project_id=project.id,
        session=db_session,
    )
    assert len(results) == 1
    assert results[0]["status"] == "executed"

    await db_session.refresh(issue)
    assert issue.status == IssueStatus.FINISHED
