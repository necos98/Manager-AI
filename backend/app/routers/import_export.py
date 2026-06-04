import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.pipeline import Pipeline, PipelineStep
from app.schemas.export_import import (
    ConflictResolveRequest,
    ImportRequest,
    ImportResult,
    ImportConflict,
)
from app.services.agent_service import AgentService
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/import", tags=["import"])


def _dedup(items: list[dict]) -> tuple[list[dict], int]:
    seen = set()
    unique = []
    skipped = 0
    for item in items:
        name = item.get("name", "")
        if not name or name in seen:
            skipped += 1
            continue
        seen.add(name)
        unique.append(item)
    return unique, skipped


def _filter_by_scope(parsed: dict, scope: str) -> tuple[list[dict], list[dict]]:
    agents = parsed.get("agents", []) or []
    pipelines = parsed.get("pipelines", []) or []
    if scope == "agents":
        pipelines = []
    elif scope == "pipelines":
        agents = []
    return agents, pipelines


@router.post("", response_model=ImportResult)
async def detect_import(data: ImportRequest, db: AsyncSession = Depends(get_db)):
    parsed = _parse(data.file_content)
    if isinstance(parsed, list):
        return ImportResult(errors=parsed)

    if not parsed.get("version"):
        return ImportResult(errors=["Invalid file format: missing 'version' field"])

    agents_data, pipelines_data = _filter_by_scope(parsed, data.scope)
    if not agents_data and not pipelines_data:
        return ImportResult(errors=["No agents or pipelines found in file"])

    unique_agents, skipped_agents = _dedup(agents_data)
    unique_pipelines, skipped_pipelines = _dedup(pipelines_data)

    agent_svc = AgentService(db)
    pipeline_svc = PipelineService(db)

    agent_names = [a["name"] for a in unique_agents if a.get("name")]
    pipeline_names = [p["name"] for p in unique_pipelines if p.get("name")]

    existing_agents = await agent_svc.get_by_names(agent_names)
    existing_pipelines = {}
    for name in pipeline_names:
        p = await pipeline_svc.get_by_name(name)
        if p:
            existing_pipelines[name] = p

    conflicts = []
    for name, agent in existing_agents.items():
        conflicts.append(ImportConflict(name=name, type="agent", existing_id=agent.id))
    for name, pipeline in existing_pipelines.items():
        conflicts.append(ImportConflict(name=name, type="pipeline", existing_id=pipeline.id))

    return ImportResult(
        created_agents=len(unique_agents) - len(existing_agents),
        skipped_agents=skipped_agents,
        created_pipelines=len(unique_pipelines) - len(existing_pipelines),
        skipped_pipelines=skipped_pipelines,
        conflicts=conflicts,
    )


@router.post("/resolve", response_model=ImportResult)
async def resolve_import(data: ConflictResolveRequest, db: AsyncSession = Depends(get_db)):
    parsed = _parse(data.file_content)
    if isinstance(parsed, list):
        return ImportResult(errors=parsed)

    agents_data, pipelines_data = _filter_by_scope(parsed, data.scope)

    if not agents_data and not pipelines_data:
        return ImportResult(errors=["No agents or pipelines found in file"])

    agent_svc = AgentService(db)
    pipeline_svc = PipelineService(db)

    overwrite_set = set(data.overwrite_ids)

    unique_agents, skipped_agents = _dedup(agents_data)
    unique_pipelines, skipped_pipelines = _dedup(pipelines_data)

    agent_names = [a["name"] for a in unique_agents if a.get("name")]
    pipeline_names = [p["name"] for p in unique_pipelines if p.get("name")]

    existing_agents = await agent_svc.get_by_names(agent_names)
    existing_pipelines = {}
    for name in pipeline_names:
        p = await pipeline_svc.get_by_name(name)
        if p:
            existing_pipelines[name] = p

    agent_map: dict[str, str] = {}

    created_agents = 0
    updated_agents = 0

    for a in unique_agents:
        name = a["name"]
        if name in existing_agents:
            agent = existing_agents[name]
            agent_map[name] = agent.id
            if agent.id in overwrite_set:
                agent.model = a.get("model")
                agent.allowed_tools = a.get("allowed_tools")
                agent.intent = a.get("intent", "")
                updated_agents += 1
        else:
            agent = await agent_svc.create(
                name=name,
                model=a.get("model"),
                allowed_tools=a.get("allowed_tools"),
                intent=a.get("intent", ""),
            )
            agent_map[name] = agent.id
            created_agents += 1

    created_pipelines = 0
    updated_pipelines = 0

    for p_data in unique_pipelines:
        name = p_data["name"]
        steps_data = p_data.get("steps", []) or []

        if name in existing_pipelines:
            pipeline = existing_pipelines[name]
            if pipeline.id in overwrite_set:
                pipeline.name = name
                for step in pipeline.steps:
                    await db.delete(step)
                pipeline.steps.clear()
                await db.flush()
                for s in steps_data:
                    agent_name = (s.get("agent", {}) or {}).get("name", "")
                    agent_id = agent_map.get(agent_name)
                    if agent_id:
                        step = PipelineStep(
                            pipeline_id=pipeline.id,
                            agent_id=agent_id,
                            order_index=s.get("order_index", 0),
                        )
                        db.add(step)
                updated_pipelines += 1
        else:
            pipeline = Pipeline(name=name)
            db.add(pipeline)
            await db.flush()
            for s in steps_data:
                agent_name = (s.get("agent", {}) or {}).get("name", "")
                agent_id = agent_map.get(agent_name)
                if agent_id:
                    step = PipelineStep(
                        pipeline_id=pipeline.id,
                        agent_id=agent_id,
                        order_index=s.get("order_index", 0),
                    )
                    db.add(step)
            created_pipelines += 1

    await db.commit()

    return ImportResult(
        created_agents=created_agents,
        updated_agents=updated_agents,
        skipped_agents=skipped_agents,
        created_pipelines=created_pipelines,
        updated_pipelines=updated_pipelines,
        skipped_pipelines=skipped_pipelines,
    )


def _parse(file_content: str) -> dict | list:
    try:
        data = json.loads(file_content)
    except json.JSONDecodeError:
        return ["Invalid file format: not valid JSON"]
    if not isinstance(data, dict):
        return ["Invalid file format: expected a JSON object"]
    return data
