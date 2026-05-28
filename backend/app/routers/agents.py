from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from app.services.agent_service import AgentService

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _response(agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        system_prompt=agent.system_prompt,
        model=agent.model,
        allowed_tools=agent.allowed_tools,
        created_at=str(agent.created_at) if agent.created_at else None,
        updated_at=str(agent.updated_at) if agent.updated_at else None,
    )


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
        system_prompt=data.system_prompt,
        model=data.model,
        allowed_tools=data.allowed_tools,
    )
    await db.commit()
    return _response(agent)


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
    agent = await svc.update(
        agent_id,
        name=data.name,
        system_prompt=data.system_prompt,
        model=data.model,
        allowed_tools=data.allowed_tools,
    )
    await db.commit()
    return _response(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    await svc.delete(agent_id)
    await db.commit()


@router.post("/seed", response_model=list[AgentResponse], status_code=201)
async def seed_agents(db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agents = await svc.seed_defaults()
    await db.commit()
    return [_response(a) for a in agents]
