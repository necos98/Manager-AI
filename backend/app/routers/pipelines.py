from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.pipeline import (
    PipelineCreate,
    PipelineResponse,
    PipelineStepCreate,
    PipelineStepResponse,
    PipelineUpdate,
    StepReorderRequest,
)
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


def _step_response(step) -> PipelineStepResponse:
    return PipelineStepResponse(
        id=step.id,
        pipeline_id=step.pipeline_id,
        agent_id=step.agent_id,
        order_index=step.order_index,
        terminal_command=step.terminal_command,
    )


def _response(pipeline) -> PipelineResponse:
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        steps=[_step_response(s) for s in (pipeline.steps or [])],
        created_at=str(pipeline.created_at) if pipeline.created_at else None,
        updated_at=str(pipeline.updated_at) if pipeline.updated_at else None,
    )


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipelines = await svc.list_all()
    return [_response(p) for p in pipelines]


@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(data: PipelineCreate, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipeline = await svc.create_pipeline(data.name)
    for step_data in data.steps:
        await svc.add_step(
            pipeline_id=pipeline.id,
            agent_id=step_data.agent_id,
            order_index=step_data.order_index,
            terminal_command=step_data.terminal_command,
        )
    await db.commit()
    return _response(await svc.get_pipeline(pipeline.id))


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipeline = await svc.get_pipeline(pipeline_id)
    return _response(pipeline)


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: str,
    data: PipelineUpdate,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    pipeline = await svc.update_pipeline(pipeline_id, data.name)
    response = _response(pipeline)
    await db.commit()
    return response


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    await svc.delete_pipeline(pipeline_id)
    await db.commit()


@router.post(
    "/{pipeline_id}/steps",
    response_model=PipelineStepResponse,
    status_code=201,
)
async def add_step(
    pipeline_id: str,
    data: PipelineStepCreate,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    step = await svc.add_step(
        pipeline_id=pipeline_id,
        agent_id=data.agent_id,
        order_index=data.order_index,
        terminal_command=data.terminal_command,
    )
    response = _step_response(step)
    await db.commit()
    return response


@router.delete("/{pipeline_id}/steps/{step_id}", status_code=204)
async def remove_step(
    pipeline_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    await svc.remove_step(step_id)
    await db.commit()


@router.put(
    "/{pipeline_id}/steps/reorder",
    response_model=list[PipelineStepResponse],
)
async def reorder_steps(
    pipeline_id: str,
    data: StepReorderRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    steps = await svc.reorder_steps(pipeline_id, data.step_ids)
    response = [_step_response(s) for s in steps]
    await db.commit()
    return response


@router.post("/seed", response_model=PipelineResponse, status_code=201)
async def seed_pipeline(db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipeline = await svc.seed_defaults()
    await db.commit()
    return _response(await svc.get_pipeline(pipeline.id))
