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
        intent=agent.intent,
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
        model=data.model,
        allowed_tools=data.allowed_tools,
        intent=data.intent or "",
    )
    resp = _response(agent)
    await db.commit()
    return resp


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


@router.post("/seed", response_model=list[AgentResponse], status_code=201)
async def seed_agents(db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agents = await svc.seed_defaults()
    resp = [_response(a) for a in agents]
    await db.commit()
    return resp
