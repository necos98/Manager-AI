from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.agent import Agent

DEFAULT_AGENTS = [
    {
        "name": "CodebaseExplorer",
        "intent": (
            "Explore the codebase to understand structure, patterns, and dependencies. "
            "Trace relevant code paths. Identify files that need changes. "
            "Document findings. Do NOT modify files — this is analysis only."
        ),
    },
    {
        "name": "BrainstormingAgent",
        "intent": (
            "Analyze the issue description and brainstorm requirements. "
            "Ask clarifying questions if needed. Write a detailed specification "
            "via create_issue_spec. Set issue name via set_issue_name."
        ),
    },
    {
        "name": "SpecWriter",
        "intent": (
            "Analyze the issue description, ask clarifying questions if needed, "
            "write a detailed specification covering requirements, constraints, "
            "and success criteria. Save via create_issue_spec. "
            "Set issue name via set_issue_name."
        ),
    },
    {
        "name": "PlanWriter",
        "intent": (
            "Review the specification. Design an implementation plan with concrete steps, "
            "identify files to create/modify, and define atomic tasks. "
            "Save via create_issue_plan and create_plan_tasks."
        ),
    },
    {
        "name": "Developer",
        "intent": (
            "Read the plan tasks via get_plan_tasks. Implement each task sequentially — "
            "update status to In Progress when starting, Completed when done. "
            "Follow existing codebase patterns. Make autonomous decisions. "
            "Do NOT ask for confirmations."
        ),
    },
    {
        "name": "Reviewer",
        "intent": (
            "Review all code changes for bugs, logic errors, security issues, "
            "and adherence to project conventions. Run the test suite. "
            "Report findings via send_agent_message with specific, "
            "actionable feedback for the QA agent."
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
                intent=data.get("intent", ""),
            )
            self.session.add(agent)
            agents.append(agent)
        await self.session.flush()
        return agents

    # ── CRUD ──────────────────────────────────────────────────────────

    async def create(
        self,
        name: str,
        model: str | None = None,
        allowed_tools: list[str] | None = None,
        intent: str = "",
    ) -> Agent:
        agent = Agent(
            name=name,
            model=model,
            allowed_tools=allowed_tools,
            intent=intent,
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
