from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentResponse
from app.services.orchestrator_service import OrchestratorService

router = APIRouter(prefix="/api/projects/{project_id}/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(project_id: str, db: AsyncSession = Depends(get_db)):
    orch = OrchestratorService(db)
    agents = await orch.ensure_default_agents(project_id)
    return [AgentResponse.from_model(a) for a in agents]


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(project_id: str, data: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(
        project_id=project_id,
        name=data.name,
        role_key=data.role_key,
        system_prompt=data.system_prompt,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.from_model(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(project_id: str, agent_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if agent is None or agent.project_id != project_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    if "name" in data:
        agent.name = data["name"]
    if "system_prompt" in data:
        agent.system_prompt = data["system_prompt"]
    if "enabled" in data:
        agent.enabled = data["enabled"]
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.from_model(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(project_id: str, agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if agent is None or agent.project_id != project_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()
