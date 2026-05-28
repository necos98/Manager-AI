from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models.pipeline import Pipeline, PipelineStep
from app.services.agent_service import AgentService, DEFAULT_AGENTS


class PipelineService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── seed ──────────────────────────────────────────────────────────

    async def seed_defaults(self) -> Pipeline:
        """Idempotent. Creates 6-step pipeline only if no pipelines exist."""
        existing = await self.list_all()
        if existing:
            return existing[0]
        agent_svc = AgentService(self.session)
        agents = await agent_svc.list_all()

        cmd_by_name = {a["name"]: a.get("terminal_command", "") for a in DEFAULT_AGENTS}

        pipeline = Pipeline(name="Default Pipeline")
        self.session.add(pipeline)
        await self.session.flush()
        for i, agent in enumerate(agents):
            step = PipelineStep(
                pipeline_id=pipeline.id,
                agent_id=agent.id,
                order_index=i,
                terminal_command=cmd_by_name.get(agent.name, ""),
            )
            self.session.add(step)
        await self.session.flush()
        return pipeline

    # ── Pipeline CRUD ─────────────────────────────────────────────────

    async def create_pipeline(self, name: str) -> Pipeline:
        pipeline = Pipeline(name=name)
        self.session.add(pipeline)
        await self.session.flush()
        return pipeline

    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        result = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.id == pipeline_id)
            .options(selectinload(Pipeline.steps))
        )
        pipeline = result.scalar_one_or_none()
        if pipeline is None:
            raise NotFoundError(f"Pipeline not found: {pipeline_id}")
        return pipeline

    async def list_all(self) -> list[Pipeline]:
        result = await self.session.execute(
            select(Pipeline)
            .options(selectinload(Pipeline.steps))
            .order_by(Pipeline.name)
        )
        return list(result.unique().scalars().all())

    async def update_pipeline(self, pipeline_id: str, name: str) -> Pipeline:
        pipeline = await self.get_pipeline(pipeline_id)
        pipeline.name = name
        await self.session.flush()
        return pipeline

    async def delete_pipeline(self, pipeline_id: str) -> bool:
        pipeline = await self.get_pipeline(pipeline_id)
        await self.session.delete(pipeline)
        await self.session.flush()
        return True

    # ── Step CRUD ─────────────────────────────────────────────────────

    async def add_step(
        self,
        pipeline_id: str,
        agent_id: str,
        order_index: int,
        terminal_command: str = "",
    ) -> PipelineStep:
        step = PipelineStep(
            pipeline_id=pipeline_id,
            agent_id=agent_id,
            order_index=order_index,
            terminal_command=terminal_command,
        )
        self.session.add(step)
        await self.session.flush()
        return step

    async def remove_step(self, step_id: str) -> bool:
        result = await self.session.execute(
            select(PipelineStep).where(PipelineStep.id == step_id)
        )
        step = result.scalar_one_or_none()
        if step is None:
            raise NotFoundError(f"Pipeline step not found: {step_id}")
        await self.session.delete(step)
        await self.session.flush()
        return True

    async def reorder_steps(
        self, pipeline_id: str, step_ids: list[str]
    ) -> list[PipelineStep]:
        steps = []
        for i, step_id in enumerate(step_ids):
            result = await self.session.execute(
                select(PipelineStep).where(
                    PipelineStep.id == step_id,
                    PipelineStep.pipeline_id == pipeline_id,
                )
            )
            step = result.scalar_one_or_none()
            if step is None:
                raise NotFoundError(f"Pipeline step not found: {step_id}")
            step.order_index = i
            steps.append(step)
        await self.session.flush()
        return steps
