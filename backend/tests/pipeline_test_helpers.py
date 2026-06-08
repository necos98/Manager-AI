"""Test helpers for pipeline integration tests.

Provides high-level functions to:
- Build pipelines with agents, steps, and event rules
- Create pipeline runs
- Simulate step execution (success, failure, rejection) without real PTY/Claude
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.issue import Issue, IssueStatus
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_event_rule import PipelineEventRule
from app.models.pipeline_run import (
    PipelineMessage,
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.models.project import Project
from app.services.pipeline_run import (
    _completion,
    _events,
    _lifecycle,
    _orchestrated,
    _queries,
    _rejection,
    _safe_session,
)
from app.services.pipeline_run._orchestrated import start_step
from app.services.pipeline_service import PipelineService
from app.utils.datetime import now


# ═════════════════════════════════════════════════════════════════════════════
# Helpers: Build
# ═════════════════════════════════════════════════════════════════════════════


async def create_agents(
    db_session: AsyncSession,
    names: list[str],
    provider: str = "claude",
) -> dict[str, Agent]:
    """Create agents by name. Returns dict {name: Agent}."""
    agents = {}
    for n in names:
        a = Agent(name=n, provider=provider, intent=f"Role: {n}")
        db_session.add(a)
        agents[n] = a
    await db_session.flush()
    return agents


async def create_pipeline(
    db_session: AsyncSession,
    agents: dict[str, Agent],
    step_order: list[tuple[str, int]],
    name: str = "Test Pipeline",
) -> tuple[Pipeline, dict[str, PipelineStep]]:
    """Create a pipeline with steps in given order.

    step_order: list of (agent_name, order_index)
    Returns (pipeline, {agent_name: PipelineStep})
    """
    pipeline = Pipeline(name=name)
    db_session.add(pipeline)
    await db_session.flush()
    steps: dict[str, PipelineStep] = {}
    for agent_name, idx in step_order:
        s = PipelineStep(
            pipeline_id=pipeline.id,
            agent_id=agents[agent_name].id,
            order_index=idx,
        )
        db_session.add(s)
        steps[agent_name] = s
    await db_session.flush()
    return pipeline, steps


async def create_project_and_issue(
    db_session: AsyncSession,
    project_name: str = "Test Project",
    issue_status: IssueStatus = IssueStatus.NEW,
) -> tuple[Project, Issue]:
    """Create a project and an issue. Returns (project, issue)."""
    project = Project(name=project_name, path="/tmp/test-pipeline-project")
    db_session.add(project)
    await db_session.flush()
    issue = Issue(
        project_id=project.id,
        description=f"Issue for {project_name}",
        status=issue_status,
    )
    db_session.add(issue)
    await db_session.flush()
    return project, issue


async def add_event_rule(
    db_session: AsyncSession,
    pipeline: Pipeline,
    source_step: PipelineStep,
    *,
    event_type: str,
    action_type: str = "redirect",
    action_params: dict[str, Any] | None = None,
) -> PipelineEventRule:
    """Add an event rule to a pipeline.

    The target_step_id is set to source_step's id (self-target).
    For 'redirect' action, override target_step_id manually.
    """
    svc = PipelineService(db_session)
    rule = await svc.add_event_rule(
        pipeline_id=pipeline.id,
        event_type=event_type,
        source_step_id=source_step.id,
        target_step_id=source_step.id,
        action_type=action_type,
        action_params=action_params,
    )
    return rule


async def create_run(
    db_session: AsyncSession,
    pipeline: Pipeline,
    issue: Issue,
    *,
    orchestrated: bool = False,
    start_at_step: int = 0,
) -> tuple[PipelineRun, list[PipelineStepRun]]:
    """Create a pipeline run with step runs (all PENDING).

    Returns (run, [step_run_0, step_run_1, ...]) ordered by order_index.
    """
    run = PipelineRun(
        pipeline_id=pipeline.id,
        issue_id=issue.id,
        status=PipelineRunStatus.WAITING_FOR_STEP if orchestrated else PipelineRunStatus.RUNNING,
        current_step_index=start_at_step,
        orchestrated=orchestrated,
        started_at=now(),
    )
    db_session.add(run)
    await db_session.flush()

    # Explicitly query steps to avoid lazy-load detachment issues
    from sqlalchemy import select
    from app.models.pipeline import PipelineStep as _PipelineStep

    rows = await db_session.execute(
        select(_PipelineStep)
        .where(_PipelineStep.pipeline_id == pipeline.id)
        .order_by(_PipelineStep.order_index)
    )
    steps = rows.scalars().all()

    step_runs: list[PipelineStepRun] = []
    for step in steps:
        sr = PipelineStepRun(
            pipeline_run_id=run.id,
            pipeline_step_id=step.id,
            status=PipelineStepRunStatus.PENDING,
        )
        db_session.add(sr)
        await db_session.flush()
        step_runs.append(sr)

    await db_session.commit()
    return run, step_runs


# ═════════════════════════════════════════════════════════════════════════════
# Helpers: Simulate
# ═════════════════════════════════════════════════════════════════════════════


async def mark_step_running(
    db_session: AsyncSession,
    run_id: str,
    step_index: int,
) -> PipelineStepRun:
    """Mark the step at given index as RUNNING (as the real loop would do)."""
    run = await _queries.get_run_with_session(run_id, db_session)
    run.current_step_index = step_index
    sr = _find_step_run(run, step_index)
    sr.status = PipelineStepRunStatus.RUNNING
    sr.started_at = now()
    await _safe_session.safe_commit(db_session)
    return sr


async def simulate_step_success(
    db_session: AsyncSession,
    run_id: str,
    project_id: str,
    *,
    advance_index: bool = True,
) -> dict[str, Any]:
    """Simulate a pipeline step completing successfully.

    Marks the current RUNNING step as COMPLETED, fires event engine,
    advances to next step (or finalizes if last step).
    This mirrors what _handle_step_completion() does in auto mode.

    Set advance_index=False for orchestrated mode (where advance_step
    manages the index).
    """
    run = await _queries.get_run_with_session(run_id, db_session)
    idx = run.current_step_index

    # Find the RUNNING step run for this index
    sr = _find_step_run(run, idx, only_running=True)
    if sr is None:
        return {"error": f"No RUNNING step run at index {idx}"}

    agent_name = sr.pipeline_step.agent.name if sr.pipeline_step and sr.pipeline_step.agent else "unknown"

    # Mark step COMPLETED (same logic as _handle_step_completion)
    sr.status = PipelineStepRunStatus.COMPLETED
    sr.finished_at = now()

    # Fire event engine for step_completed
    await _events.fire_pipeline_event(
        run.pipeline_id, "step_completed",
        sr.pipeline_step_id,
        run_id=run_id, issue_id=run.issue_id, project_id=project_id,
        agent_name=agent_name, step_run_id=sr.id,
        step_index=idx,
        session=db_session,
    )

    # Check if this was the last step
    total_steps = len([s for s in run.step_runs if s.pipeline_step])
    is_last = idx + 1 >= total_steps

    if is_last and advance_index:
        # Auto-mode: pipeline completes when last step finishes
        run.status = PipelineRunStatus.COMPLETED
        run.finished_at = now()

        # Fire event engine for pipeline_completed
        await _events.fire_pipeline_event(
            run.pipeline_id, "pipeline_completed", None,
            run_id=run_id, issue_id=run.issue_id, project_id=project_id,
            metadata={"status": PipelineRunStatus.COMPLETED.value},
            session=db_session,
        )
    if advance_index and not is_last:
        run.current_step_index = idx + 1

    await _safe_session.safe_commit(db_session)

    return {
        "step_index": idx,
        "agent_name": agent_name,
        "status": "COMPLETED",
        "pipeline_finished": is_last and advance_index,
    }


async def simulate_step_failure(
    db_session: AsyncSession,
    run_id: str,
    project_id: str,
) -> dict[str, Any]:
    """Simulate a pipeline step failing.

    Marks current RUNNING step as FAILED, pipeline as FAILED.
    """
    run = await _queries.get_run_with_session(run_id, db_session)
    idx = run.current_step_index

    sr = _find_step_run(run, idx, only_running=True)
    if sr is None:
        return {"error": f"No RUNNING step run at index {idx}"}

    agent_name = sr.pipeline_step.agent.name if sr.pipeline_step and sr.pipeline_step.agent else "unknown"

    sr.status = PipelineStepRunStatus.FAILED
    sr.finished_at = now()
    run.status = PipelineRunStatus.FAILED
    run.finished_at = now()

    # Fire event engine for step_failed
    await _events.fire_pipeline_event(
        run.pipeline_id, "step_failed",
        sr.pipeline_step_id,
        run_id=run_id, issue_id=run.issue_id, project_id=project_id,
        agent_name=agent_name, step_run_id=sr.id,
        step_index=idx,
        session=db_session,
    )

    await _safe_session.safe_commit(db_session)

    return {
        "step_index": idx,
        "agent_name": agent_name,
        "status": "FAILED",
    }


async def simulate_rejection(
    db_session: AsyncSession,
    run_id: str,
    reason: str,
    target_step_index: int,
    project_id: str,
) -> dict[str, Any]:
    """Simulate a step rejection (redirect to previous step).

    Delegates to the real reject_step() from _rejection module.
    """
    return await _rejection.reject_step(
        run_id=run_id,
        reason=reason,
        target_step_index=target_step_index,
        project_id=project_id,
        session=db_session,
    )


async def simulate_orchestrated_step_end(
    db_session: AsyncSession,
    run_id: str,
    step_index: int,
) -> dict[str, Any]:
    """Simulate the orchestrated step completion signal.

    In orchestrated mode, this is called when the worker calls
    finished_pipeline_step via MCP. It signals the completion event
    so monitor_step can pick it up.
    """
    ok = _completion.set_step_completed(run_id, step_index)
    return {"step_completed": ok}


async def simulate_step_running_for_test(
    db_session: AsyncSession,
    run_id: str,
    step_index: int,
) -> PipelineStepRun:
    """Set the pipeline state as if a step just started.

    Used by tests that need a real RUNNING state before simulating
    rejection or failure.
    """
    run = await _queries.get_run_with_session(run_id, db_session)
    run.current_step_index = step_index
    run.status = PipelineRunStatus.RUNNING

    sr = _find_step_run(run, step_index)
    sr.status = PipelineStepRunStatus.RUNNING
    sr.started_at = now()

    await _safe_session.safe_commit(db_session)
    return sr


# ═════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═════════════════════════════════════════════════════════════════════════════


def _find_step_run(
    run: PipelineRun,
    step_index: int,
    only_running: bool = False,
) -> PipelineStepRun | None:
    """Find the step run for a given step index."""
    for sr in run.step_runs:
        if sr.pipeline_step and sr.pipeline_step.order_index == step_index:
            if only_running and sr.status != PipelineStepRunStatus.RUNNING:
                continue
            return sr
    return None
