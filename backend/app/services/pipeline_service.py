from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models.pipeline import Pipeline, PipelineStep
from app.services.agent_service import AgentService


class PipelineService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── seed ──────────────────────────────────────────────────────────

    async def seed_defaults(self, project_id: str) -> Pipeline:
        """Idempotent. Creates 6-step pipeline only if project has 0 pipelines."""
        existing = await self.list_by_project(project_id)
        if existing:
            return existing[0]
        agent_svc = AgentService(self.session)
        agents = await agent_svc.list_by_project(project_id)
        pipeline = Pipeline(project_id=project_id, name="Default Pipeline")
        self.session.add(pipeline)
        await self.session.flush()
        for i, agent in enumerate(agents):
            step = PipelineStep(
                pipeline_id=pipeline.id,
                agent_id=agent.id,
                order_index=i,
                terminal_command="",
            )
            self.session.add(step)
        await self.session.flush()
        return pipeline

    # ── Pipeline CRUD ─────────────────────────────────────────────────

    async def create_pipeline(self, project_id: str, name: str) -> Pipeline:
        pipeline = Pipeline(project_id=project_id, name=name)
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

    async def list_by_project(self, project_id: str) -> list[Pipeline]:
        result = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.project_id == project_id)
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
