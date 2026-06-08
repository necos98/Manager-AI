"""Database read queries for pipeline runs."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.exceptions import NotFoundError
from app.models.issue import Issue
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import PipelineRun, PipelineRunStatus, PipelineStepRun
from app.services.pipeline_run._responses import active_run_to_dict, run_to_dict


# ── Eager-load helpers ─────────────────────────────────────────

_PIPELINE_LOAD = joinedload(PipelineRun.pipeline)
_STEP_RUNS_LOAD = (
    joinedload(PipelineRun.step_runs)
    .joinedload(PipelineStepRun.pipeline_step)
    .joinedload(PipelineStep.agent)
)
_FULL_RUN_LOAD = [_PIPELINE_LOAD, _STEP_RUNS_LOAD]


# ── Core loader ────────────────────────────────────────────────


async def get_run_with_session(run_id: str, session: AsyncSession) -> PipelineRun:
    """Get a pipeline run with all eager-loaded relationships."""
    result = await session.execute(
        select(PipelineRun)
        .where(PipelineRun.id == run_id)
        .options(*_FULL_RUN_LOAD)
    )
    run = result.unique().scalar_one_or_none()
    if run is None:
        raise NotFoundError(f"Pipeline run not found: {run_id}")
    return run


# ── Public query methods ──────────────────────────────────────


async def get_run(run_id: str, session: AsyncSession) -> dict:
    """Get a single pipeline run with its step runs."""
    run = await get_run_with_session(run_id, session)
    return run_to_dict(run)


async def get_runs_for_issue(issue_id: str, session: AsyncSession) -> list[dict]:
    """Get all pipeline runs for an issue, ordered by creation date desc."""
    result = await session.execute(
        select(PipelineRun)
        .where(PipelineRun.issue_id == issue_id)
        .options(*_FULL_RUN_LOAD)
        .order_by(PipelineRun.created_at.desc())
    )
    runs = result.unique().scalars().all()
    return [run_to_dict(r) for r in runs]


async def get_active_runs_for_issues(
    issue_ids: list[str], session: AsyncSession
) -> dict[str, dict | None]:
    """Return active (RUNNING) pipeline runs for given issue ids."""
    result = await session.execute(
        select(PipelineRun)
        .where(
            PipelineRun.issue_id.in_(issue_ids),
            PipelineRun.status == PipelineRunStatus.RUNNING,
        )
        .options(_PIPELINE_LOAD)
    )
    runs = result.unique().scalars().all()
    run_by_issue: dict[str, dict | None] = {iid: None for iid in issue_ids}
    for r in runs:
        run_by_issue[r.issue_id] = active_run_to_dict(r)
    return run_by_issue


async def get_active_runs_for_project(
    project_id: str, session: AsyncSession
) -> list[dict]:
    """Return active (RUNNING) pipeline runs for a project via Issue JOIN."""
    result = await session.execute(
        select(PipelineRun)
        .join(Issue, PipelineRun.issue_id == Issue.id)
        .where(
            Issue.project_id == project_id,
            PipelineRun.status == PipelineRunStatus.RUNNING,
        )
        .options(*_FULL_RUN_LOAD)
        .order_by(PipelineRun.created_at.desc())
    )
    runs = result.unique().scalars().all()
    return [run_to_dict(r) for r in runs]
