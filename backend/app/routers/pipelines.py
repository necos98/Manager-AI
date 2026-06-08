from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.pipeline import PipelineCreate, PipelineResponse, PipelineStepCreate, PipelineStepResponse, PipelineUpdate, StepReorderRequest
from app.schemas.pipeline_event_rule import PipelineEventRuleCreate, PipelineEventRuleResponse, PipelineEventRuleUpdate
from app.schemas.export_import import ImportConfirmResponse, PipelineBatchExportRequest, PipelineImportPreviewResponse
from app.services.pipeline_service import PipelineService, _response, _rule_response, _step_response
from app.services.pipeline_export import export_pipelines_all as _export_all, export_pipelines_batch as _export_batch, export_pipeline_single as _export_single
from app.services.pipeline_import import import_pipelines_preview as _import_preview, import_pipelines_confirm as _import_confirm

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


# ── Static paths ──


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(db: AsyncSession = Depends(get_db)):
    return [_response(p) for p in await PipelineService(db).list_all()]

@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(data: PipelineCreate, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    p = await svc.create_pipeline(data.name)
    for s in data.steps:
        await svc.add_step(p.id, s.agent_id, s.order_index)
    await db.commit()
    return _response(await svc.get_pipeline(p.id))

@router.post("/seed", response_model=PipelineResponse, status_code=201)
async def seed_pipeline(db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    p = await svc.seed_defaults()
    await db.commit()
    return _response(await svc.get_pipeline(p.id))

@router.get("/export")
async def export_pipelines_all(db: AsyncSession = Depends(get_db)):
    return await _export_all(db)

@router.post("/export/batch")
async def export_pipelines_batch(request: PipelineBatchExportRequest, db: AsyncSession = Depends(get_db)):
    return await _export_batch(request.pipeline_ids, db)

@router.get("/export/{pipeline_id}")
async def export_pipeline_single(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    return await _export_single(pipeline_id, db)

@router.post("/import/preview", response_model=PipelineImportPreviewResponse)
async def import_pipelines_preview(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are supported")
    raw = await file.read()
    return await _import_preview(raw, db)

@router.post("/import/confirm", response_model=ImportConfirmResponse)
async def import_pipelines_confirm(file: UploadFile = File(...), conflicts: str = Form("{}"), db: AsyncSession = Depends(get_db)):
    raw = await file.read()
    return await _import_confirm(raw, conflicts, db)


# ── Parameterized paths ──


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    return _response(await PipelineService(db).get_pipeline(pipeline_id))

@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(pipeline_id: str, data: PipelineUpdate, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    await svc.update_pipeline(pipeline_id, data.name)
    await db.commit()
    return _response(await svc.get_pipeline(pipeline_id))

@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    await svc.delete_pipeline(pipeline_id)
    await db.commit()

@router.post("/{pipeline_id}/steps", response_model=PipelineStepResponse, status_code=201)
async def add_step(pipeline_id: str, data: PipelineStepCreate, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    step = await svc.add_step(pipeline_id=pipeline_id, agent_id=data.agent_id, order_index=data.order_index)
    await db.commit()
    return _step_response(step)

@router.delete("/{pipeline_id}/steps/{step_id}", status_code=204)
async def remove_step(pipeline_id: str, step_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    await svc.remove_step(step_id)
    await db.commit()

@router.put("/{pipeline_id}/steps/reorder", response_model=list[PipelineStepResponse])
async def reorder_steps(pipeline_id: str, data: StepReorderRequest, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    steps = await svc.reorder_steps(pipeline_id, data.step_ids)
    await db.commit()
    return [_step_response(s) for s in steps]

@router.get("/{pipeline_id}/event-rules", response_model=list[PipelineEventRuleResponse])
async def list_event_rules(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    return [_rule_response(r) for r in await PipelineService(db).list_event_rules(pipeline_id)]

@router.post("/{pipeline_id}/event-rules", response_model=PipelineEventRuleResponse, status_code=201)
async def create_event_rule(pipeline_id: str, data: PipelineEventRuleCreate, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    try:
        rule = await svc.add_event_rule(pipeline_id=pipeline_id, event_type=data.event_type, source_step_id=data.source_step_id, target_step_id=data.target_step_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()
    return _rule_response(rule)

@router.put("/{pipeline_id}/event-rules/{rule_id}", response_model=PipelineEventRuleResponse)
async def update_event_rule(pipeline_id: str, rule_id: str, data: PipelineEventRuleUpdate, db: AsyncSession = Depends(get_db)):
    """Update specific fields on an event rule. Only provided fields are changed."""
    svc = PipelineService(db)
    try:
        kwargs = data.model_dump(exclude_none=True)
        rule = await svc.update_event_rule(rule_id, **kwargs)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()
    return _rule_response(rule)

@router.delete("/{pipeline_id}/event-rules/{rule_id}", status_code=204)
async def delete_event_rule(pipeline_id: str, rule_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    try:
        await svc.remove_event_rule(rule_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()
