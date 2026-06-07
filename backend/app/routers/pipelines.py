import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, NotFoundError
from app.schemas.pipeline import (
    PipelineCreate,
    PipelineResponse,
    PipelineStepCreate,
    PipelineStepResponse,
    PipelineUpdate,
    StepReorderRequest,
)
from app.schemas.pipeline_event_rule import (
    PipelineEventRuleCreate,
    PipelineEventRuleResponse,
)
from app.schemas.export_import import (
    ImportConfirmResponse,
    ImportConflict,
    MissingAgentInfo,
    PipelineBatchExportRequest,
    PipelineImportPreviewResponse,
    build_export_wrapper,
    format_pipeline_export,
)
from app.services.agent_service import AgentService
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


def _step_response(step) -> PipelineStepResponse:
    return PipelineStepResponse(
        id=step.id,
        pipeline_id=step.pipeline_id,
        agent_id=step.agent_id,
        order_index=step.order_index,
    )


def _response(pipeline) -> PipelineResponse:
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        steps=[_step_response(s) for s in (pipeline.steps or [])],
        created_at=str(pipeline.created_at) if pipeline.created_at else None,
        updated_at=str(pipeline.updated_at) if pipeline.updated_at else None,
    )


# ── Static paths before parameterized paths ──


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
        )
    await db.commit()
    return _response(await svc.get_pipeline(pipeline.id))


@router.post("/seed", response_model=PipelineResponse, status_code=201)
async def seed_pipeline(db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipeline = await svc.seed_defaults()
    await db.commit()
    return _response(await svc.get_pipeline(pipeline.id))


@router.get("/export")
async def export_pipelines_all(db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipelines = await svc.export_all()
    items = [format_pipeline_export(p) for p in pipelines]
    wrapper = build_export_wrapper("pipelines", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="pipelines-export.json"'},
    )


@router.post("/export/batch")
async def export_pipelines_batch(
    request: PipelineBatchExportRequest,
    db: AsyncSession = Depends(get_db),
):
    if not request.pipeline_ids:
        raise HTTPException(status_code=400, detail="pipeline_ids must not be empty")
    svc = PipelineService(db)
    items = await svc.export_batch(request.pipeline_ids)
    wrapper = build_export_wrapper("pipelines", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="pipelines-export.json"'},
    )


@router.get("/export/{pipeline_id}")
async def export_pipeline_single(
    pipeline_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    try:
        pipeline = await svc.export_by_id(pipeline_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")
    items = [format_pipeline_export(pipeline)]
    wrapper = build_export_wrapper("pipelines", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="pipeline-{pipeline_id}.json"'
        },
    )


@router.post("/import/preview", response_model=PipelineImportPreviewResponse)
async def import_pipelines_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are supported")

    try:
        raw = await file.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if data.get("version") != 1:
        raise HTTPException(status_code=400, detail="Unsupported export version")
    if data.get("type") != "pipelines":
        raise HTTPException(
            status_code=400,
            detail=f"Expected type 'pipelines', got '{data.get('type')}'",
        )

    items = data.get("items", [])
    svc = PipelineService(db)
    agent_svc = AgentService(db)

    conflicts = []
    new_items = []
    missing_agents_list = []
    all_agent_ids_in_file = set()

    # Collect all agent IDs referenced in the file
    for item in items:
        for step in item.get("steps", []):
            aid = step.get("agent_id")
            if aid:
                all_agent_ids_in_file.add(aid)

    # Check which agent IDs exist in DB
    existing_agent_ids = await agent_svc.check_agent_ids_exist(
        list(all_agent_ids_in_file)
    )

    for item in items:
        pipeline_id = item.get("id")
        if not pipeline_id:
            continue

        # Check for missing agents in this pipeline's steps
        for step in item.get("steps", []):
            aid = step.get("agent_id")
            if aid and aid not in existing_agent_ids:
                agent_data = step.get("agent", {})
                if not agent_data or not agent_data.get("id"):
                    missing_agents_list.append(
                        MissingAgentInfo(
                            agent_id=aid,
                            name=agent_data.get("name", "Unknown"),
                        )
                    )

        try:
            existing = await svc.get_pipeline(pipeline_id)
            conflicts.append(
                ImportConflict(
                    incoming=item,
                    existing={
                        "id": existing.id,
                        "name": existing.name,
                        "steps": [
                            {"id": s.id, "agent_id": s.agent_id, "order_index": s.order_index}
                            for s in (existing.steps or [])
                        ],
                    },
                )
            )
        except NotFoundError:
            new_items.append(item)

    return PipelineImportPreviewResponse(
        conflicts=conflicts,
        new=new_items,
        missing_agents=missing_agents_list,
        total=len(items),
    )


@router.post("/import/confirm", response_model=ImportConfirmResponse)
async def import_pipelines_confirm(
    file: UploadFile = File(...),
    conflicts: str = Form("{}"),
    db: AsyncSession = Depends(get_db),
):
    try:
        raw = await file.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if data.get("type") != "pipelines":
        raise HTTPException(
            status_code=400,
            detail=f"Expected type 'pipelines', got '{data.get('type')}'",
        )

    try:
        conflict_map = json.loads(conflicts)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid conflicts format")

    # Extract all referenced agents from the file
    items = data.get("items", [])
    file_agents = []
    for item in items:
        for step in item.get("steps", []):
            agent_data = step.get("agent")
            if agent_data and agent_data.get("id"):
                file_agents.append(agent_data)

    agent_svc = AgentService(db)
    svc = PipelineService(db)

    result = await svc.import_pipelines(items, file_agents, conflict_map, agent_svc)
    await db.commit()
    return result


# ── Parameterized paths ──


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
    await svc.update_pipeline(pipeline_id, data.name)
    await db.commit()
    return _response(await svc.get_pipeline(pipeline_id))


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


def _rule_response(rule) -> PipelineEventRuleResponse:
    return PipelineEventRuleResponse(
        id=rule.id,
        pipeline_id=rule.pipeline_id,
        event_type=rule.event_type,
        source_step_id=rule.source_step_id,
        target_step_id=rule.target_step_id,
        enabled=rule.enabled,
        created_at=str(rule.created_at) if rule.created_at else None,
        updated_at=str(rule.updated_at) if rule.updated_at else None,
    )


@router.get(
    "/{pipeline_id}/event-rules",
    response_model=list[PipelineEventRuleResponse],
)
async def list_event_rules(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    rules = await svc.list_event_rules(pipeline_id)
    return [_rule_response(r) for r in rules]


@router.post(
    "/{pipeline_id}/event-rules",
    response_model=PipelineEventRuleResponse,
    status_code=201,
)
async def create_event_rule(
    pipeline_id: str,
    data: PipelineEventRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    try:
        rule = await svc.add_event_rule(
            pipeline_id=pipeline_id,
            event_type=data.event_type,
            source_step_id=data.source_step_id,
            target_step_id=data.target_step_id,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()
    return _rule_response(rule)


@router.delete(
    "/{pipeline_id}/event-rules/{rule_id}",
    status_code=204,
)
async def delete_event_rule(
    pipeline_id: str,
    rule_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    try:
        await svc.remove_event_rule(rule_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    await db.commit()
