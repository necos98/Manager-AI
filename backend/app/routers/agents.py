import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from app.schemas.export_import import (
    AgentBatchExportRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
    ImportConflict,
    build_export_wrapper,
    format_agent_export,
)
from app.services.agent_service import AgentService

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _response(agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        intent=agent.intent,
        model=agent.model,
        allowed_tools=agent.allowed_tools,
        created_at=str(agent.created_at) if agent.created_at else None,
        updated_at=str(agent.updated_at) if agent.updated_at else None,
    )


# ── Static paths before parameterized paths ──


@router.get("", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agents = await svc.list_all()
    return [_response(a) for a in agents]


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agent = await svc.create(
        name=data.name,
        model=data.model,
        allowed_tools=data.allowed_tools,
        intent=data.intent or "",
    )
    resp = _response(agent)
    await db.commit()
    return resp


@router.post("/seed", response_model=list[AgentResponse], status_code=201)
async def seed_agents(db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agents = await svc.seed_defaults()
    resp = [_response(a) for a in agents]
    await db.commit()
    return resp


@router.get("/export")
async def export_agents_all(db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agents = await svc.export_all()
    items = [format_agent_export(a) for a in agents]
    wrapper = build_export_wrapper("agents", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="agents-export.json"'},
    )


@router.post("/export/batch")
async def export_agents_batch(
    request: AgentBatchExportRequest,
    db: AsyncSession = Depends(get_db),
):
    if not request.agent_ids:
        raise HTTPException(status_code=400, detail="agent_ids must not be empty")
    svc = AgentService(db)
    items = await svc.export_batch(request.agent_ids)
    wrapper = build_export_wrapper("agents", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="agents-export.json"'},
    )


@router.get("/export/{agent_id}")
async def export_agent_single(agent_id: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    try:
        agent = await svc.export_by_id(agent_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    items = [format_agent_export(agent)]
    wrapper = build_export_wrapper("agents", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="agent-{agent_id}.json"'},
    )


@router.post("/import/preview", response_model=ImportPreviewResponse)
async def import_agents_preview(
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
    if data.get("type") != "agents":
        raise HTTPException(
            status_code=400,
            detail=f"Expected type 'agents', got '{data.get('type')}'",
        )

    items = data.get("items", [])
    svc = AgentService(db)
    conflicts = []
    new_items = []

    for item in items:
        agent_id = item.get("id")
        if not agent_id:
            continue
        try:
            existing = await svc.get_by_id(agent_id)
            conflicts.append(
                ImportConflict(
                    incoming=item,
                    existing=format_agent_export(existing),
                )
            )
        except NotFoundError:
            new_items.append(item)

    return ImportPreviewResponse(
        conflicts=conflicts,
        new=new_items,
        total=len(items),
    )


@router.post("/import/confirm", response_model=ImportConfirmResponse)
async def import_agents_confirm(
    file: UploadFile = File(...),
    conflicts: str = Form("{}"),
    db: AsyncSession = Depends(get_db),
):
    try:
        raw = await file.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if data.get("type") != "agents":
        raise HTTPException(
            status_code=400,
            detail=f"Expected type 'agents', got '{data.get('type')}'",
        )

    try:
        conflict_map = json.loads(conflicts)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid conflicts format")

    svc = AgentService(db)
    items = data.get("items", [])
    result = await svc.import_agents(items, conflict_map)
    await db.commit()
    return result


# ── Parameterized paths ──


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agent = await svc.get_by_id(agent_id)
    return _response(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
):
    svc = AgentService(db)
    kwargs = {}
    if data.name is not None:
        kwargs["name"] = data.name
    if data.intent is not None:
        kwargs["intent"] = data.intent
    if data.model is not None:
        kwargs["model"] = data.model
    if data.allowed_tools is not None:
        kwargs["allowed_tools"] = data.allowed_tools
    agent = await svc.update(agent_id, **kwargs)
    resp = _response(agent)
    await db.commit()
    return resp


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    await svc.delete(agent_id)
    await db.commit()
