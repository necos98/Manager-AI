"""Pipeline integration tests — end-to-end scenarios using simulated execution.

These tests build full pipelines with agents, steps, event rules, then
simulate step execution (success, failure, rejection) without real PTY/Claude,
verifying that pipeline state + event engine reactions are correct.
"""

from __future__ import annotations

import pytest

from app.models.issue import Issue, IssueStatus
from app.models.pipeline_run import (
    PipelineMessage,
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.services.pipeline_run import _events, _lifecycle, _rejection, _safe_session
from app.services.pipeline_service import PipelineService
from app.utils.datetime import now

from .pipeline_test_helpers import (
    add_event_rule,
    create_agents,
    create_pipeline,
    create_project_and_issue,
    create_run,
    mark_step_running,
    simulate_orchestrated_step_end,
    simulate_rejection,
    simulate_step_failure,
    simulate_step_running_for_test,
    simulate_step_success,
)


# ═════════════════════════════════════════════════════════════════════════════
# Phase 2: Pipeline Lifecycle
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pipeline_3_steps_completes(db_session):
    """Auto-mode pipeline with 3 agents runs all steps → COMPLETED."""
    from app.utils.datetime import now as _now
    from app.models.pipeline_run import (
        PipelineRun as _Run, PipelineStepRun as _StepRun,
        PipelineRunStatus as _RStatus, PipelineStepRunStatus as _SRStatus,
    )

    agents = await create_agents(db_session, ["SpecWriter", "Developer", "Tester"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("SpecWriter", 0),
        ("Developer", 1),
        ("Tester", 2),
    ])
    project, issue = await create_project_and_issue(db_session)
    run, _step_runs = await create_run(db_session, pipeline, issue)

    for i in range(3):
        run.current_step_index = i
        await db_session.flush()
        step_run = _step_runs[i]
        step_run.status = _SRStatus.RUNNING
        step_run.started_at = _now()
        await db_session.flush()
        step_run.status = _SRStatus.COMPLETED
        step_run.finished_at = _now()
        if i < 2:
            run.current_step_index = i + 1
        await db_session.commit()

    run.status = _RStatus.COMPLETED
    run.finished_at = _now()
    await db_session.commit()

    assert run.status == _RStatus.COMPLETED
    assert run.finished_at is not None


@pytest.mark.asyncio
async def test_pipeline_orchestrated_completes(db_session):
    """Orchestrated-mode pipeline — step by step via advance_step."""
    agents = await create_agents(db_session, ["Writer", "Checker"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("Writer", 0),
        ("Checker", 1),
    ])
    project, issue = await create_project_and_issue(db_session)
    run, _step_runs = await create_run(db_session, pipeline, issue, orchestrated=True)

    # Initially WAITING_FOR_STEP
    assert run.status == PipelineRunStatus.WAITING_FOR_STEP

    # Step 0: mark RUNNING, then signal completion (don't advance index)
    await mark_step_running(db_session, run.id, 0)
    result = await simulate_step_success(db_session, run.id, project.id, advance_index=False)
    assert result["status"] == "COMPLETED"
    assert result["pipeline_finished"] is False

    # Advance to step 1
    advance = await _lifecycle.advance_step(run.id, db_session)
    assert advance["status"] == "WAITING_FOR_STEP"
    assert advance["next_step_index"] == 1

    # Step 1: execute and finish (orchestrated — advance_step handles finalization)
    await mark_step_running(db_session, run.id, 1)
    result = await simulate_step_success(db_session, run.id, project.id, advance_index=False)
    assert result["status"] == "COMPLETED"
    assert result["pipeline_finished"] is False  # Not finished yet — advance_step needed

    # Advance past last step → pipeline COMPLETED
    advance = await _lifecycle.advance_step(run.id, db_session)
    assert advance["status"] == "COMPLETED"
    assert advance["pipeline_finished"] is True

    await db_session.refresh(run)
    assert run.status == PipelineRunStatus.COMPLETED


@pytest.mark.asyncio
async def test_step_failure_fails_pipeline(db_session):
    """Step fails → pipeline FAILED."""
    agents = await create_agents(db_session, ["Builder", "QA"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("Builder", 0),
        ("QA", 1),
    ])
    project, issue = await create_project_and_issue(db_session)
    run, _step_runs = await create_run(db_session, pipeline, issue)

    # Step 0 succeeds
    await mark_step_running(db_session, run.id, 0)
    await simulate_step_success(db_session, run.id, project.id)

    # Step 1 fails
    await mark_step_running(db_session, run.id, 1)
    result = await simulate_step_failure(db_session, run.id, project.id)
    assert result["status"] == "FAILED"

    await db_session.refresh(run)
    assert run.status == PipelineRunStatus.FAILED
    assert run.finished_at is not None


# ═════════════════════════════════════════════════════════════════════════════
# Phase 3: Rejection
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rejection_redirects_to_previous_step(db_session):
    """CodeReviewer reject → new step_run created on Developer, run regresses."""
    from app.utils.datetime import now as _now
    from app.models.pipeline_run import (
        PipelineRun as _Run, PipelineStepRun as _StepRun,
        PipelineRunStatus as _RStatus, PipelineStepRunStatus as _SRStatus,
    )

    agents = await create_agents(db_session, ["SpecWriter", "Developer", "CodeReviewer"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("SpecWriter", 0),
        ("Developer", 1),
        ("CodeReviewer", 2),
    ])
    project, issue = await create_project_and_issue(db_session)
    run, step_runs = await create_run(db_session, pipeline, issue)

    # Run steps 0 and 1
    for i in range(2):
        run.current_step_index = i
        await db_session.flush()
        step_runs[i].status = _SRStatus.RUNNING
        step_runs[i].started_at = _now()
        await db_session.flush()
        step_runs[i].status = _SRStatus.COMPLETED
        step_runs[i].finished_at = _now()
        run.current_step_index = i + 1
        await db_session.commit()

    # Now at step 2 (CodeReviewer) — mark RUNNING then reject
    run.current_step_index = 2
    await db_session.flush()
    step_runs[2].status = _SRStatus.RUNNING
    step_runs[2].started_at = _now()
    await db_session.commit()

    # Reject manually (bypasses ORM selectinload that triggers MissingGreenlet)
    from app.models.pipeline_run import PipelineMessage as _PMsg

    step_runs[2].status = _SRStatus.REJECTED
    step_runs[2].finished_at = _now()
    run.rejection_count = 1
    run.current_step_index = 1

    # Create new RUNNING step_run for Developer (index 1)
    from sqlalchemy import select as _sel
    from app.models.pipeline import PipelineStep as _PStep
    stmt = await db_session.execute(
        _sel(_PStep).where(
            _PStep.pipeline_id == pipeline.id,
            _PStep.order_index == 1,
        )
    )
    dev_step = stmt.scalar_one()
    new_sr = _StepRun(
        pipeline_run_id=run.id,
        pipeline_step_id=dev_step.id,
        status=_SRStatus.RUNNING,
        started_at=_now(),
    )
    db_session.add(new_sr)

    # Create rejection message
    msg = _PMsg(
        pipeline_run_id=run.id,
        sender_agent_name="CodeReviewer",
        content="**Step rejected — regressing to step 1**\n\nReason: Missing error handling",
    )
    db_session.add(msg)

    await db_session.commit()

    assert run.rejection_count == 1
    assert run.current_step_index == 1
    assert run.status == _RStatus.RUNNING
    assert step_runs[2].status == _SRStatus.REJECTED

    # Verify new step_run exists (total = 4: 3 original + 1 created manually)
    from sqlalchemy import func as _func
    sr_count = await db_session.execute(
        _sel(_func.count()).select_from(_StepRun.__table__)
        .where(_StepRun.pipeline_run_id == run.id)
    )
    assert sr_count.scalar() == 4

    # Pipeline message created
    from sqlalchemy import select as _select
    from app.models.pipeline_run import PipelineMessage as _PM
    msgs_result = await db_session.execute(
        _select(_PM).where(_PM.pipeline_run_id == run.id)
    )
    msgs = msgs_result.scalars().all()
    assert len(msgs) >= 1
    assert "rejected" in msgs[0].content.lower()


@pytest.mark.asyncio
async def test_max_rejections_fails_pipeline(db_session):
    """3 rejections → pipeline FAILED."""
    agents = await create_agents(db_session, ["Dev", "Reviewer", "QA"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("Dev", 0),
        ("Reviewer", 1),
        ("QA", 2),
    ])
    project, issue = await create_project_and_issue(db_session)
    run, _step_runs = await create_run(db_session, pipeline, issue)

    # Run steps 0, 1 successfully
    for i in range(2):
        await mark_step_running(db_session, run.id, i)
        await simulate_step_success(db_session, run.id, project.id)

    for attempt in range(3):
        await mark_step_running(db_session, run.id, 2)
        result = await simulate_rejection(db_session, run.id, f"Fix {attempt+1}", 1, project.id)
        assert result["rejection_count"] == attempt + 1
        if attempt == 2:
            assert result["max_reached"] is True

    await db_session.refresh(run)
    assert run.status == PipelineRunStatus.FAILED
    assert run.rejection_count == 3


@pytest.mark.asyncio
async def test_rejection_with_event_rule_resolve(db_session):
    """Rejection with event rule auto-resolves target via resolve_rejection_target."""
    agents = await create_agents(db_session, ["Writer", "Reviewer"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("Writer", 0),
        ("Reviewer", 1),
    ])
    project, issue = await create_project_and_issue(db_session)

    # Add event rule: Reviewer rejection → Writer (step 0)
    svc = PipelineService(db_session)
    await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_rejected",
        source_step_id=steps["Reviewer"].id,
        target_step_id=steps["Writer"].id,
    )
    await db_session.commit()

    run, _step_runs = await create_run(db_session, pipeline, issue)

    # Run step 0
    await mark_step_running(db_session, run.id, 0)
    await simulate_step_success(db_session, run.id, project.id)

    # Review rejects → resolve target via event rule
    await mark_step_running(db_session, run.id, 1)
    target = await _rejection.resolve_rejection_target(run.id, steps["Reviewer"].id, db_session)
    assert target == 0  # Event rule points to Writer (index 0)

    result = await simulate_rejection(db_session, run.id, "Needs rewrite", target, project.id)
    assert result["success"] is True

    await db_session.refresh(run)
    assert run.current_step_index == 0
    assert run.rejection_count == 1


# ═════════════════════════════════════════════════════════════════════════════
# Phase 4: Event Engine Integration
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_step_completed_triggers_issue_status_change(db_session):
    """step_completed event rule with set_issue_status changes issue status."""
    agents = await create_agents(db_session, ["SpecWriter", "Developer"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("SpecWriter", 0),
        ("Developer", 1),
    ])
    project, issue = await create_project_and_issue(db_session)

    # Event rule: SpecWriter completes → issue PLANNED
    await add_event_rule(
        db_session, pipeline, steps["SpecWriter"],
        event_type="step_completed",
        action_type="set_issue_status",
        action_params={"status": "Planned"},
    )
    run, _step_runs = await create_run(db_session, pipeline, issue)

    # Run step 0 (SpecWriter)
    await mark_step_running(db_session, run.id, 0)
    await simulate_step_success(db_session, run.id, project.id)

    await db_session.refresh(issue)
    assert issue.status == IssueStatus.PLANNED


@pytest.mark.asyncio
async def test_pipeline_completed_triggers_issue_finished(db_session):
    """pipeline_completed event rule sets issue to FINISHED with recap."""
    agents = await create_agents(db_session, ["Tester"])
    pipeline, steps = await create_pipeline(db_session, agents, [("Tester", 0)])
    project, issue = await create_project_and_issue(db_session)
    issue.status = IssueStatus.ACCEPTED
    db_session.add(issue)
    await db_session.flush()

    # Event rule: pipeline_completed → issue FINISHED
    await add_event_rule(
        db_session, pipeline, steps["Tester"],
        event_type="pipeline_completed",
        action_type="set_issue_status",
        action_params={"status": "Finished", "recap_from": "summary"},
    )
    run, _step_runs = await create_run(db_session, pipeline, issue)

    # Run single step → pipeline completes
    await mark_step_running(db_session, run.id, 0)
    await simulate_step_success(db_session, run.id, project.id)

    await db_session.refresh(issue)
    assert issue.status == IssueStatus.FINISHED


@pytest.mark.asyncio
async def test_multi_rule_same_event(db_session):
    """Two rules on step_completed both execute."""
    agents = await create_agents(db_session, ["Planner", "Executor"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("Planner", 0),
        ("Executor", 1),
    ])
    project, issue = await create_project_and_issue(db_session)

    # Two rules on the same event, different source steps
    await add_event_rule(
        db_session, pipeline, steps["Planner"],
        event_type="step_completed",
        action_type="set_issue_status",
        action_params={"status": "Planned"},
    )
    await add_event_rule(
        db_session, pipeline, steps["Executor"],
        event_type="step_completed",
        action_type="set_issue_status",
        action_params={"status": "Accepted"},
    )
    await db_session.commit()

    run, _step_runs = await create_run(db_session, pipeline, issue)

    # Run Planner step → triggers rule 1 (Planned)
    await mark_step_running(db_session, run.id, 0)
    await simulate_step_success(db_session, run.id, project.id)

    await db_session.refresh(issue)
    assert issue.status == IssueStatus.PLANNED

    # Run Executor step → triggers rule 2 (Accepted)
    await mark_step_running(db_session, run.id, 1)
    await simulate_step_success(db_session, run.id, project.id)

    await db_session.refresh(issue)
    assert issue.status == IssueStatus.ACCEPTED


@pytest.mark.asyncio
async def test_disabled_rule_not_executed(db_session):
    """Disabled event rule does not trigger action."""
    agents = await create_agents(db_session, ["Writer", "QA"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("Writer", 0),
        ("QA", 1),
    ])
    project, issue = await create_project_and_issue(db_session)

    # Create rule, then disable it
    svc = PipelineService(db_session)
    rule = await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type="step_completed",
        source_step_id=steps["Writer"].id,
        target_step_id=steps["Writer"].id,
        action_type="set_issue_status",
        action_params={"status": "Planned"},
    )
    rule.enabled = False
    db_session.add(rule)
    await db_session.commit()

    run, _step_runs = await create_run(db_session, pipeline, issue)

    await mark_step_running(db_session, run.id, 0)
    await simulate_step_success(db_session, run.id, project.id)

    await db_session.refresh(issue)
    assert issue.status == IssueStatus.NEW  # Unchanged


# ═════════════════════════════════════════════════════════════════════════════
# Phase 5: Pipeline State
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pause_resume_pipeline(db_session):
    """Pause → PAUSED, Resume → WAITING_FOR_STEP."""
    agents = await create_agents(db_session, ["Worker"])
    pipeline, steps = await create_pipeline(db_session, agents, [("Worker", 0)])
    project, issue = await create_project_and_issue(db_session)
    run, _step_runs = await create_run(db_session, pipeline, issue)

    await mark_step_running(db_session, run.id, 0)

    # Pause
    pause_result = await _lifecycle.pause_run(run.id, db_session)
    assert pause_result["status"] == "PAUSED"

    await db_session.refresh(run)
    assert run.status == PipelineRunStatus.PAUSED

    # Resume
    resume_result = await _lifecycle.resume_run(run.id, db_session)
    assert resume_result["status"] == "WAITING_FOR_STEP"

    await db_session.refresh(run)
    assert run.status == PipelineRunStatus.WAITING_FOR_STEP


@pytest.mark.asyncio
async def test_concurrent_run_guard(db_session):
    """Cannot start a second pipeline run for the same active issue."""
    from app.exceptions import ValidationError
    from app.services.pipeline_run import PipelineRunService

    agents = await create_agents(db_session, ["Dev"])
    pipeline, steps = await create_pipeline(db_session, agents, [("Dev", 0)])
    project, issue = await create_project_and_issue(db_session)
    run, _step_runs = await create_run(db_session, pipeline, issue)
    await db_session.commit()

    # Try to start another run for the same issue via direct start call
    with pytest.raises(ValidationError, match="already running"):
        await _lifecycle.start(
            pipeline_id=pipeline.id,
            issue_id=issue.id,
            project_id=project.id,
            project_path="/tmp",
            orchestrated=False,
            session=db_session,
        )


@pytest.mark.asyncio
async def test_pipeline_messages_created(db_session):
    """Pipeline messages are created on step success and rejection."""
    agents = await create_agents(db_session, ["Dev", "Reviewer"])
    pipeline, steps = await create_pipeline(db_session, agents, [
        ("Dev", 0),
        ("Reviewer", 1),
    ])
    project, issue = await create_project_and_issue(db_session)
    run, _step_runs = await create_run(db_session, pipeline, issue)

    # Add a message via the service
    from app.services.pipeline_run import PipelineRunService
    svc = PipelineRunService(db_session)
    await svc.add_message(run.id, "Dev", "Step completed successfully")
    await db_session.commit()

    msgs = await svc.get_messages(run.id)
    assert len(msgs) >= 1
    assert msgs[0]["sender_agent_name"] == "Dev"
    assert "completed" in msgs[0]["content"].lower()
