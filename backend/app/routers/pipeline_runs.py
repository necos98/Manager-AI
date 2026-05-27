from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.exceptions import AppError
from app.models.project import Project
from app.schemas.pipeline_run import (
    PipelineMessageCreate,
    PipelineMessageResponse,
    PipelineRunResponse,
    PipelineRunStart,
)
from app.services.pipeline_run_service import PipelineRunService

router = APIRouter(
    prefix="/api/projects/{project_id}/pipeline-runs", tags=["pipeline-runs"]
)


async def _get_project_path(project_id: str, db: AsyncSession) -> str:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project.path


@router.post("", response_model=PipelineRunResponse, status_code=201)
async def start_pipeline_run(
    project_id: str,
    data: PipelineRunStart,
    db: AsyncSession = Depends(get_db),
):
    project_path = await _get_project_path(project_id, db)
    svc = PipelineRunService(db, session_factory=async_session)
    try:
        result = await svc.start(
            pipeline_id=data.pipeline_id,
            issue_id=data.issue_id,
            project_id=project_id,
            project_path=project_path,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()
    return result


@router.get("", response_model=list[PipelineRunResponse])
async def list_pipeline_runs(
    project_id: str,
    issue_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineRunService(db)
    return await svc.get_runs_for_issue(issue_id)


@router.get("/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineRunService(db)
    try:
        return await svc.get_run(run_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/{run_id}", status_code=204)
async def cancel_pipeline_run(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineRunService(db)
    try:
        await svc.cancel_run(run_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()


@router.get("/{run_id}/messages", response_model=list[PipelineMessageResponse])
async def get_pipeline_messages(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineRunService(db)
    return await svc.get_messages(run_id)


@router.post(
    "/{run_id}/messages",
    response_model=PipelineMessageResponse,
    status_code=201,
)
async def send_pipeline_message(
    project_id: str,
    run_id: str,
    data: PipelineMessageCreate,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineRunService(db)
    try:
        result = await svc.add_message(
            run_id=run_id,
            sender_agent_name=data.sender_agent_name,
            content=data.content,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()
    return result
