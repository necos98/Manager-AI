from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_event_rule import PipelineEventRule
from app.services.agent_service import AgentService
from app.schemas.pipeline import PipelineResponse, PipelineStepResponse
from app.schemas.pipeline_event_rule import PipelineEventRuleResponse


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

        pipeline = Pipeline(name="Default Pipeline")
        self.session.add(pipeline)
        await self.session.flush()
        for i, agent in enumerate(agents):
            step = PipelineStep(
                pipeline_id=pipeline.id,
                agent_id=agent.id,
                order_index=i,
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
    ) -> PipelineStep:
        result = await self.session.execute(
            select(func.max(PipelineStep.order_index)).where(
                PipelineStep.pipeline_id == pipeline_id
            )
        )
        max_idx = result.scalar()
        next_idx = (max_idx + 1) if max_idx is not None else 0

        step = PipelineStep(
            pipeline_id=pipeline_id,
            agent_id=agent_id,
            order_index=next_idx,
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
        # Two-pass with no_autoflush: assign temp indices first (no conflict),
        # flush, then assign final indices. This avoids the UNIQUE constraint
        # violation that occurs when autoflush fires mid-loop.
        offset = len(step_ids)
        with self.session.sync_session.no_autoflush:
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
                step.order_index = offset + i
                steps.append(step)
            await self.session.flush()

            for i, step in enumerate(steps):
                step.order_index = i
            await self.session.flush()

        return steps

    # ── Event Rule CRUD ─────────────────────────────────────────────

    async def add_event_rule(
        self,
        pipeline_id: str,
        event_type: str,
        source_step_id: str,
        target_step_id: str,
        action_type: str = "redirect",
        action_params: dict | None = None,
    ) -> PipelineEventRule:
        """Add an event rule with step ID validation."""
        pipeline = await self.get_pipeline(pipeline_id)
        step_ids = {s.id for s in pipeline.steps}
        if source_step_id not in step_ids:
            raise NotFoundError(f"source_step_id {source_step_id} not in pipeline steps")
        if target_step_id not in step_ids:
            raise NotFoundError(f"target_step_id {target_step_id} not in pipeline steps")
        rule = PipelineEventRule(
            pipeline_id=pipeline_id,
            event_type=event_type,
            source_step_id=source_step_id,
            target_step_id=target_step_id,
            action_type=action_type,
            action_params=action_params,
        )
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def remove_event_rule(self, rule_id: str) -> bool:
        result = await self.session.execute(
            select(PipelineEventRule).where(PipelineEventRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise NotFoundError(f"PipelineEventRule not found: {rule_id}")
        await self.session.delete(rule)
        await self.session.flush()
        return True

    async def list_event_rules(self, pipeline_id: str) -> list[PipelineEventRule]:
        result = await self.session.execute(
            select(PipelineEventRule)
            .where(PipelineEventRule.pipeline_id == pipeline_id)
            .order_by(PipelineEventRule.created_at)
        )
        return list(result.scalars().all())

    async def get_event_rule_for_step(
        self, pipeline_id: str, event_type: str, source_step_id: str
    ) -> PipelineEventRule | None:
        result = await self.session.execute(
            select(PipelineEventRule).where(
                PipelineEventRule.pipeline_id == pipeline_id,
                PipelineEventRule.event_type == event_type,
                PipelineEventRule.source_step_id == source_step_id,
                PipelineEventRule.enabled.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def update_event_rule(
        self, rule_id: str, **kwargs: object,
    ) -> PipelineEventRule:
        """Update specific fields on an event rule. Only provided kwargs are set."""
        result = await self.session.execute(
            select(PipelineEventRule).where(PipelineEventRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise NotFoundError(f"PipelineEventRule not found: {rule_id}")

        for key, value in kwargs.items():
            if value is not None and hasattr(rule, key):
                setattr(rule, key, value)

        await self.session.flush()
        return rule


# ── Serializers ──────────────────────────────────────────────


def _step_response(step) -> PipelineStepResponse:
    return PipelineStepResponse(
        id=step.id,
        pipeline_id=step.pipeline_id,
        agent_id=step.agent_id,
        order_index=step.order_index,
    )


def _response(pipeline) -> PipelineResponse:
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        steps=[_step_response(s) for s in (pipeline.steps or [])],
        created_at=str(pipeline.created_at) if pipeline.created_at else None,
        updated_at=str(pipeline.updated_at) if pipeline.updated_at else None,
    )


def _rule_response(rule) -> PipelineEventRuleResponse:
    return PipelineEventRuleResponse(
        id=rule.id,
        pipeline_id=rule.pipeline_id,
        event_type=rule.event_type,
        source_step_id=rule.source_step_id,
        target_step_id=rule.target_step_id,
        action_type=rule.action_type,
        action_params=rule.action_params,
        enabled=rule.enabled,
        created_at=str(rule.created_at) if rule.created_at else None,
        updated_at=str(rule.updated_at) if rule.updated_at else None,
    )
