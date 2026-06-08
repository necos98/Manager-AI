"""Response / serialization builders for PipelineRun and PipelineStepRun objects.

ELIMINA LA DUPLICAZIONE: il pattern step_run -> dict ora vive in un unico posto.
Tutti i metodi get_* e start() usano questi builder.
"""

from app.models.pipeline_run import (
    PipelineRun,
    PipelineStepRun,
    PipelineStepRunStatus,
)


def step_run_to_dict(
    sr: PipelineStepRun,
    include_intent: bool = False,
) -> dict:
    """Convert a PipelineStepRun to a dictionary.

    Questo è il builder centrale. Tutti i metodi get_* usano questo, non
    costruiscono dict manualmente.
    """
    agent_name = "unknown"
    agent_intent = ""
    if sr.pipeline_step and sr.pipeline_step.agent:
        agent_name = sr.pipeline_step.agent.name
        agent_intent = sr.pipeline_step.agent.intent or ""

    result = {
        "id": sr.id,
        "pipeline_run_id": sr.pipeline_run_id,
        "pipeline_step_id": sr.pipeline_step_id,
        "agent_name": agent_name,
        "status": sr.status.value,
        "terminal_id": sr.terminal_id,
        "started_at": sr.started_at.isoformat() if sr.started_at else None,
        "finished_at": sr.finished_at.isoformat() if sr.finished_at else None,
    }
    if include_intent:
        result["agent_intent"] = agent_intent
    return result


def run_to_dict(run: PipelineRun) -> dict:
    """Convert a PipelineRun + its step_runs to a full dictionary."""
    steps = []
    for sr in sorted(
        run.step_runs,
        key=lambda s: s.pipeline_step.order_index if s.pipeline_step else 0,
    ):
        steps.append(step_run_to_dict(sr, include_intent=True))

    return {
        "id": run.id,
        "pipeline_id": run.pipeline_id,
        "pipeline_name": run.pipeline.name if run.pipeline else "",
        "issue_id": run.issue_id,
        "status": run.status.value,
        "current_step_index": run.current_step_index,
        "steps": steps,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def active_run_to_dict(run: PipelineRun) -> dict:
    """Compact dict for active runs (no step sub-list)."""
    return {
        "pipeline_name": run.pipeline.name if run.pipeline else "",
        "status": run.status.value,
    }


def start_step_run_to_dict(sr: PipelineStepRun) -> dict:
    """Minimal dict for step runs created during pipeline start (no intent/terminal yet)."""
    agent_name = "unknown"
    if sr.pipeline_step and sr.pipeline_step.agent:
        agent_name = sr.pipeline_step.agent.name
    return {
        "id": sr.id,
        "pipeline_run_id": sr.pipeline_run_id,
        "pipeline_step_id": sr.pipeline_step_id,
        "agent_name": agent_name,
        "status": PipelineStepRunStatus.PENDING.value,
        "terminal_id": None,
    }
