from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.pipeline import AgentStepRun, Pipeline, PipelineRun
from app.schemas.pipeline import PipelineCreate, PipelineResponse, PipelineRunFullResponse
from app.services.orchestrator_service import OrchestratorService

router = APIRouter(prefix="/api/projects/{project_id}/pipelines", tags=["pipelines"])


def _pipeline_to_dict(p: Pipeline) -> dict:
    return {
        "id": p.id,
        "project_id": p.project_id,
        "name": p.name,
        "steps": json.loads(p.steps) if p.steps else [],
        "is_default": p.is_default,
        "trigger_type": p.trigger_type,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("")
async def list_pipelines(project_id: str, db: AsyncSession = Depends(get_db)):
    orch = OrchestratorService(db)
    await orch.ensure_default_agents(project_id)
    pipeline = await orch.ensure_default_pipeline(project_id)
    result = await db.execute(
        select(Pipeline).where(Pipeline.project_id == project_id).order_by(Pipeline.name)
    )
    pipelines = result.scalars().all()
    return {"pipelines": [_pipeline_to_dict(p) for p in pipelines]}


@router.post("", status_code=201)
async def create_pipeline(project_id: str, data: PipelineCreate, db: AsyncSession = Depends(get_db)):
    if data.is_default:
        await db.execute(
            update(Pipeline)
            .where(Pipeline.project_id == project_id, Pipeline.is_default == True)
            .values(is_default=False)
        )
    pipeline = Pipeline(
        project_id=project_id,
        name=data.name,
        steps=json.dumps([s.model_dump() for s in data.steps]),
        is_default=data.is_default,
        trigger_type=data.trigger_type,
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    return _pipeline_to_dict(pipeline)


@router.put("/{pipeline_id}")
async def update_pipeline(project_id: str, pipeline_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    pipeline = await db.get(Pipeline, pipeline_id)
    if pipeline is None or pipeline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if "name" in data:
        pipeline.name = data["name"]
    if "steps" in data:
        pipeline.steps = json.dumps(data["steps"])
    if "trigger_type" in data:
        pipeline.trigger_type = data["trigger_type"]
    if data.get("is_default"):
        await db.execute(
            update(Pipeline)
            .where(Pipeline.project_id == project_id, Pipeline.is_default == True)
            .values(is_default=False)
        )
        pipeline.is_default = True
    elif "is_default" in data:
        pipeline.is_default = data["is_default"]
    await db.commit()
    await db.refresh(pipeline)
    return _pipeline_to_dict(pipeline)


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(project_id: str, pipeline_id: str, db: AsyncSession = Depends(get_db)):
    pipeline = await db.get(Pipeline, pipeline_id)
    if pipeline is None or pipeline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await db.delete(pipeline)
    await db.commit()


@router.get("/runs/{run_id}")
async def get_pipeline_run(run_id: str, db: AsyncSession = Depends(get_db)):
    pipeline_run = await db.get(PipelineRun, run_id)
    if pipeline_run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    steps = await db.execute(
        select(AgentStepRun)
        .where(AgentStepRun.pipeline_run_id == run_id)
        .order_by(AgentStepRun.step_order)
    )
    step_list = steps.scalars().all()
    return {
        "run": {
            "id": pipeline_run.id,
            "pipeline_id": pipeline_run.pipeline_id,
            "issue_id": pipeline_run.issue_id,
            "trigger_type": pipeline_run.trigger_type,
            "status": pipeline_run.status.value,
            "started_at": pipeline_run.started_at.isoformat() if pipeline_run.started_at else None,
            "completed_at": pipeline_run.completed_at.isoformat() if pipeline_run.completed_at else None,
        },
        "steps": [
            {
                "id": s.id,
                "agent_name": s.agent_name,
                "agent_role": s.agent_role,
                "step_order": s.step_order,
                "status": s.status.value,
                "summary": s.summary,
                "error": s.error,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in step_list
        ],
    }


@router.get("/runs/by-issue/{issue_id}")
async def get_pipeline_runs_for_issue(issue_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.issue_id == issue_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(5)
    )
    runs = result.scalars().all()
    return {
        "runs": [
            {
                "id": r.id,
                "status": r.status.value,
                "trigger_type": r.trigger_type,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]
    }
