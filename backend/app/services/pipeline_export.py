"""Pipeline export service functions."""

import json

from fastapi import HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline import Pipeline, PipelineStep
from app.schemas.export_import import build_export_wrapper, format_pipeline_export


async def export_pipelines_all(db: AsyncSession) -> Response:
    """Export all pipelines."""
    result = await db.execute(
        select(Pipeline)
        .options(
            selectinload(Pipeline.steps).selectinload(PipelineStep.agent),
            selectinload(Pipeline.event_rules),
        )
        .order_by(Pipeline.name)
    )
    pipelines = list(result.unique().scalars().all())
    items = [format_pipeline_export(p) for p in pipelines]
    wrapper = build_export_wrapper("pipelines", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="pipelines-export.json"'},
    )


async def export_pipelines_batch(
    pipeline_ids: list[str], db: AsyncSession
) -> Response:
    """Export specific pipelines by ID."""
    if not pipeline_ids:
        raise HTTPException(status_code=400, detail="pipeline_ids must not be empty")
    result = await db.execute(
        select(Pipeline)
        .where(Pipeline.id.in_(pipeline_ids))
        .options(
            selectinload(Pipeline.steps).selectinload(PipelineStep.agent),
            selectinload(Pipeline.event_rules),
        )
        .order_by(Pipeline.name)
    )
    pipelines = result.unique().scalars().all()
    items = [format_pipeline_export(p) for p in pipelines]
    wrapper = build_export_wrapper("pipelines", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="pipelines-export.json"'},
    )


async def export_pipeline_single(pipeline_id: str, db: AsyncSession) -> Response:
    """Export a single pipeline by ID."""
    result = await db.execute(
        select(Pipeline)
        .where(Pipeline.id == pipeline_id)
        .options(
            selectinload(Pipeline.steps).selectinload(PipelineStep.agent),
            selectinload(Pipeline.event_rules),
        )
    )
    pipeline = result.scalar_one_or_none()
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )
    items = [format_pipeline_export(pipeline)]
    wrapper = build_export_wrapper("pipelines", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="pipeline-{pipeline_id}.json"'
        },
    )
