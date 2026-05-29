from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.agent import Agent

DEFAULT_AGENTS = [
    {
        "name": "CodebaseExplorer",
        "system_prompt": (
            "Explore and analyze codebase structure, find patterns and conventions, "
            "trace execution paths, and document dependencies."
        ),
    },
    {
        "name": "BrainstormingAgent",
        "system_prompt": (
            "Brainstorm ideas and refine requirements through natural collaborative dialogue. "
            "Turn ideas into fully formed designs and specs."
        ),
    },
    {
        "name": "SpecWriter",
        "system_prompt": (
            "Write detailed specifications from requirements. Produce clear, structured "
            "specs covering architecture, components, data flow, error handling, and testing."
        ),
    },
    {
        "name": "PlanWriter",
        "system_prompt": (
            "Create implementation plans from specifications. Break down designs into "
            "atomic, ordered tasks with specific files to create or modify."
        ),
    },
    {
        "name": "Developer",
        "system_prompt": (
            "Implement code following plans and specifications. Write production-quality "
            "code that follows existing patterns and conventions."
        ),
    },
    {
        "name": "Reviewer",
        "system_prompt": (
            "Review code for bugs, logic errors, security vulnerabilities, code quality "
            "issues, and adherence to project conventions."
        ),
    },
]


class AgentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── seed ──────────────────────────────────────────────────────────

    async def seed_defaults(self) -> list[Agent]:
        """Idempotent. Creates 6 default agents only if no agents exist."""
        existing = await self.list_all()
        if existing:
            return existing
        agents = []
        for data in DEFAULT_AGENTS:
            agent = Agent(
                name=data["name"],
                system_prompt=data["system_prompt"],
            )
            self.session.add(agent)
            agents.append(agent)
        await self.session.flush()
        return agents

    # ── CRUD ──────────────────────────────────────────────────────────

    async def create(
        self,
        name: str,
        system_prompt: str,
        model: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> Agent:
        agent = Agent(
            name=name,
            system_prompt=system_prompt,
            model=model,
            allowed_tools=allowed_tools,
        )
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def get_by_id(self, agent_id: str) -> Agent:
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            raise NotFoundError(f"Agent not found: {agent_id}")
        return agent

    async def get_by_name(self, name: str) -> Agent | None:
        result = await self.session.execute(
            select(Agent).where(Agent.name == name)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Agent]:
        result = await self.session.execute(
            select(Agent).order_by(Agent.name)
        )
        return list(result.scalars().all())

    async def update(self, agent_id: str, **kwargs) -> Agent:
        agent = await self.get_by_id(agent_id)
        for key, value in kwargs.items():
            if value is not None and hasattr(agent, key):
                setattr(agent, key, value)
        await self.session.flush()
        return agent

    async def delete(self, agent_id: str) -> bool:
        agent = await self.get_by_id(agent_id)
        await self.session.delete(agent)
        await self.session.flush()
        return True
