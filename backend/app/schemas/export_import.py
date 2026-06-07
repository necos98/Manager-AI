from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel


class AgentBatchExportRequest(BaseModel):
    agent_ids: list[str]


class PipelineBatchExportRequest(BaseModel):
    pipeline_ids: list[str]


class AgentExportItem(BaseModel):
    id: str
    name: str
    model: str | None = None
    allowed_tools: list[str] | None = None
    intent: str = ""


class PipelineStepExportItem(BaseModel):
    id: str
    pipeline_id: str
    agent_id: str
    order_index: int
    agent: AgentExportItem


class PipelineExportItem(BaseModel):
    id: str
    name: str
    steps: list[PipelineStepExportItem]


def build_export_wrapper(
    type_: Literal["agents", "pipelines"],
    items: list[dict],
) -> dict:
    return {
        "version": 1,
        "type": type_,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": items,
    }


def format_agent_export(agent) -> dict:
    return {
        "id": agent.id,
        "name": agent.name,
        "model": agent.model,
        "allowed_tools": agent.allowed_tools,
        "intent": agent.intent,
    }


def format_pipeline_step_export(step) -> dict:
    return {
        "id": step.id,
        "pipeline_id": step.pipeline_id,
        "agent_id": step.agent_id,
        "order_index": step.order_index,
        "agent": {
            "id": step.agent.id,
            "name": step.agent.name,
            "model": step.agent.model,
            "allowed_tools": step.agent.allowed_tools,
            "intent": step.agent.intent,
        },
    }


def format_pipeline_event_rule_export(rule) -> dict:
    return {
        "id": rule.id,
        "event_type": rule.event_type,
        "source_step_id": rule.source_step_id,
        "target_step_id": rule.target_step_id,
        "enabled": rule.enabled,
    }


def format_pipeline_export(pipeline) -> dict:
    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "steps": [format_pipeline_step_export(s) for s in (pipeline.steps or [])],
        "event_rules": [format_pipeline_event_rule_export(r) for r in (pipeline.event_rules or [])],
    }


class ImportConflict(BaseModel):
    incoming: dict
    existing: dict


class ImportPreviewResponse(BaseModel):
    conflicts: list[ImportConflict]
    new: list[dict]
    total: int


class MissingAgentInfo(BaseModel):
    agent_id: str
    name: str


class PipelineImportPreviewResponse(BaseModel):
    conflicts: list[ImportConflict]
    new: list[dict]
    missing_agents: list[MissingAgentInfo]
    total: int


class ImportConfirmResponse(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
