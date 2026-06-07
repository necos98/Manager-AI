"""Pipeline import service functions."""

import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_event_rule import PipelineEventRule
from app.schemas.export_import import (
    ImportConfirmResponse,
    ImportConflict,
    MissingAgentInfo,
    PipelineImportPreviewResponse,
)
from app.services.agent_service import AgentService


async def import_pipelines_preview(
    raw: bytes, db: AsyncSession
) -> PipelineImportPreviewResponse:
    """Preview importing pipelines from raw JSON bytes."""
    try:
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

    conflicts: list[ImportConflict] = []
    new_items: list[dict] = []
    missing_agents_list: list[MissingAgentInfo] = []
    all_agent_ids_in_file: set[str] = set()

    for item in items:
        for step in item.get("steps", []):
            aid = step.get("agent_id")
            if aid:
                all_agent_ids_in_file.add(aid)

    agent_svc = AgentService(db)
    existing_agent_ids = await agent_svc.check_agent_ids_exist(
        list(all_agent_ids_in_file)
    )

    for item in items:
        pipeline_id = item.get("id")
        if not pipeline_id:
            continue

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

        result = await db.execute(
            select(Pipeline)
            .where(Pipeline.id == pipeline_id)
            .options(selectinload(Pipeline.steps))
        )
        existing = result.scalar_one_or_none()
        if existing:
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
        else:
            new_items.append(item)

    return PipelineImportPreviewResponse(
        conflicts=conflicts,
        new=new_items,
        missing_agents=missing_agents_list,
        total=len(items),
    )


async def import_pipelines_confirm(
    raw: bytes, conflicts: str, db: AsyncSession
) -> ImportConfirmResponse:
    """Execute pipeline import with conflict resolution."""
    try:
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

    items = data.get("items", [])
    file_agents = []
    for item in items:
        for step in item.get("steps", []):
            agent_data = step.get("agent")
            if agent_data and agent_data.get("id"):
                file_agents.append(agent_data)

    result = await _import_pipelines(items, file_agents, conflict_map, db)
    await db.commit()
    return result


async def _import_pipelines(
    pipelines_data: list[dict],
    file_agents: list[dict],
    conflict_map: dict[str, str],
    db: AsyncSession,
) -> ImportConfirmResponse:
    imported = 0
    skipped = 0
    errors = []

    all_agent_ids_in_file = {a.get("id") for a in file_agents if a.get("id")}
    agent_svc = AgentService(db)
    existing_agent_ids = await agent_svc.check_agent_ids_exist(
        list(all_agent_ids_in_file)
    )

    for item in pipelines_data:
        pipeline_id = item.get("id")
        if not pipeline_id:
            errors.append(f"Pipeline item missing id: {item.get('name', '?')}")
            continue

        try:
            result = await db.execute(
                select(Pipeline)
                .where(Pipeline.id == pipeline_id)
                .options(selectinload(Pipeline.steps))
            )
            existing_pipeline = result.scalar_one_or_none()

            if existing_pipeline:
                action = conflict_map.get(pipeline_id, "skip")
                if action != "overwrite":
                    skipped += 1
                    continue

                existing_pipeline.name = item.get("name", existing_pipeline.name)
                steps_data = item.get("steps", [])
                for sd in steps_data:
                    agent_id = sd.get("agent_id")
                    agent_data = sd.get("agent")
                    if agent_id not in existing_agent_ids and agent_data:
                        _ensure_agent(agent_id, agent_data, db, existing_agent_ids)
                await db.flush()
                new_steps = await _replace_steps(pipeline_id, steps_data, db)
                await _import_event_rules(
                    pipeline_id, item.get("event_rules", []), steps_data, new_steps, db
                )
                imported += 1

            else:
                pipeline = Pipeline(id=pipeline_id, name=item.get("name", "Unknown"))
                db.add(pipeline)
                await db.flush()

                steps_data = item.get("steps", [])
                for sd in steps_data:
                    agent_id = sd.get("agent_id")
                    agent_data = sd.get("agent")
                    if agent_id not in existing_agent_ids and agent_data:
                        _ensure_agent(agent_id, agent_data, db, existing_agent_ids)
                await db.flush()
                new_steps = await _replace_steps(pipeline.id, steps_data, db)
                await _import_event_rules(
                    pipeline.id, item.get("event_rules", []), steps_data, new_steps, db
                )
                imported += 1

        except Exception as e:
            errors.append(f"Error importing pipeline {pipeline_id}: {e}")

    return ImportConfirmResponse(
        imported=imported,
        skipped=skipped,
        errors=errors,
    )


def _ensure_agent(
    agent_id: str,
    agent_data: dict,
    db: AsyncSession,
    existing_ids: set[str],
) -> None:
    agent = Agent(
        id=agent_id,
        name=agent_data.get("name", "Unknown"),
        model=agent_data.get("model"),
        allowed_tools=agent_data.get("allowed_tools"),
        intent=agent_data.get("intent", ""),
    )
    db.add(agent)
    existing_ids.add(agent_id)


async def _replace_steps(
    pipeline_id: str,
    steps_data: list[dict],
    db: AsyncSession,
) -> list[PipelineStep]:
    result = await db.execute(
        select(PipelineStep).where(PipelineStep.pipeline_id == pipeline_id)
    )
    for step in result.scalars().all():
        await db.delete(step)
    await db.flush()

    new_steps = []
    for sd in steps_data:
        step = PipelineStep(
            pipeline_id=pipeline_id,
            agent_id=sd["agent_id"],
            order_index=sd.get("order_index", 0),
        )
        db.add(step)
        new_steps.append(step)
    await db.flush()
    return new_steps


async def _import_event_rules(
    pipeline_id: str,
    event_rules_data: list[dict],
    steps_data: list[dict],
    new_steps: list[PipelineStep],
    db: AsyncSession,
) -> None:
    if not event_rules_data:
        return

    existing = await db.execute(
        select(PipelineEventRule).where(
            PipelineEventRule.pipeline_id == pipeline_id
        )
    )
    for r in existing.scalars().all():
        await db.delete(r)
    await db.flush()

    old_to_new = {}
    for i, sd in enumerate(steps_data):
        old_id = sd.get("id")
        if old_id and i < len(new_steps):
            old_to_new[old_id] = new_steps[i].id

    for rule_data in event_rules_data:
        new_source = old_to_new.get(rule_data.get("source_step_id", ""))
        new_target = old_to_new.get(rule_data.get("target_step_id", ""))
        if new_source and new_target:
            rule = PipelineEventRule(
                pipeline_id=pipeline_id,
                event_type=rule_data["event_type"],
                source_step_id=new_source,
                target_step_id=new_target,
                enabled=rule_data.get("enabled", True),
            )
            db.add(rule)
    await db.flush()
