from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_event_rule import PipelineEventRule
from app.models.agent import Agent
from app.services.agent_service import AgentService
from app.schemas.export_import import ImportConfirmResponse, format_pipeline_export


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

    # ── Export / Import ────────────────────────────────────────────────

    async def export_batch(self, pipeline_ids: list[str]) -> list[dict]:
        result = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.id.in_(pipeline_ids))
            .options(
                selectinload(Pipeline.steps).selectinload(PipelineStep.agent),
                selectinload(Pipeline.event_rules),
            )
            .order_by(Pipeline.name)
        )
        pipelines = result.unique().scalars().all()
        return [format_pipeline_export(p) for p in pipelines]

    async def export_all(self) -> list[Pipeline]:
        result = await self.session.execute(
            select(Pipeline)
            .options(
                selectinload(Pipeline.steps).selectinload(PipelineStep.agent),
                selectinload(Pipeline.event_rules),
            )
            .order_by(Pipeline.name)
        )
        return list(result.unique().scalars().all())

    async def export_by_id(self, pipeline_id: str) -> Pipeline:
        result = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.id == pipeline_id)
            .options(
                selectinload(Pipeline.steps).selectinload(PipelineStep.agent),
                selectinload(Pipeline.event_rules),
            )
        )
        pipeline = result.scalar_one_or_none()
        if pipeline is None:
            raise NotFoundError(f"Pipeline not found: {pipeline_id}")
        return pipeline

    async def replace_steps(
        self,
        pipeline_id: str,
        steps_data: list[dict],
    ) -> list[PipelineStep]:
        """Delete all existing steps and create new ones with exact order_index."""
        # Delete existing steps
        result = await self.session.execute(
            select(PipelineStep).where(PipelineStep.pipeline_id == pipeline_id)
        )
        for step in result.scalars().all():
            await self.session.delete(step)
        await self.session.flush()

        # Create new steps
        new_steps = []
        for sd in steps_data:
            step = PipelineStep(
                pipeline_id=pipeline_id,
                agent_id=sd["agent_id"],
                order_index=sd.get("order_index", 0),
            )
            self.session.add(step)
            new_steps.append(step)
        await self.session.flush()
        return new_steps

    async def import_pipelines(
        self,
        pipelines_data: list[dict],
        file_agents: list[dict],  # agents from the same file's step.agent fields
        conflict_map: dict[str, str],
        agent_service: AgentService,
    ) -> ImportConfirmResponse:
        imported = 0
        skipped = 0
        errors = []

        # First pass: ensure all referenced agents exist
        all_agent_ids_in_file = {a.get("id") for a in file_agents if a.get("id")}
        existing_agent_ids = await agent_service.check_agent_ids_exist(
            list(all_agent_ids_in_file)
        )

        for item in pipelines_data:
            pipeline_id = item.get("id")
            if not pipeline_id:
                errors.append(f"Pipeline item missing id: {item.get('name', '?')}")
                continue

            try:
                existing_pipeline = await self.get_pipeline(pipeline_id)
                action = conflict_map.get(pipeline_id, "skip")
                if action != "overwrite":
                    skipped += 1
                    continue

                # Overwrite: update name and replace steps
                existing_pipeline.name = item.get("name", existing_pipeline.name)
                steps_data = item.get("steps", [])
                # Ensure referenced agents exist
                for sd in steps_data:
                    agent_id = sd.get("agent_id")
                    agent_data = sd.get("agent")
                    if agent_id and agent_id not in existing_agent_ids and agent_data:
                        # Create the agent
                        agent = Agent(
                            id=agent_id,
                            name=agent_data.get("name", "Unknown"),
                            model=agent_data.get("model"),
                            allowed_tools=agent_data.get("allowed_tools"),
                            intent=agent_data.get("intent", ""),
                        )
                        self.session.add(agent)
                        existing_agent_ids.add(agent_id)
                await self.session.flush()
                new_steps = await self.replace_steps(pipeline_id, steps_data)
                await self._import_event_rules(
                    pipeline_id, item.get("event_rules", []), steps_data, new_steps
                )
                imported += 1

            except NotFoundError:
                # New pipeline
                pipeline = Pipeline(
                    id=pipeline_id,
                    name=item.get("name", "Unknown"),
                )
                self.session.add(pipeline)
                await self.session.flush()

                steps_data = item.get("steps", [])
                for sd in steps_data:
                    agent_id = sd.get("agent_id")
                    agent_data = sd.get("agent")
                    if agent_id and agent_id not in existing_agent_ids and agent_data:
                        agent = Agent(
                            id=agent_id,
                            name=agent_data.get("name", "Unknown"),
                            model=agent_data.get("model"),
                            allowed_tools=agent_data.get("allowed_tools"),
                            intent=agent_data.get("intent", ""),
                        )
                        self.session.add(agent)
                        existing_agent_ids.add(agent_id)
                await self.session.flush()
                new_steps = await self.replace_steps(pipeline.id, steps_data)
                await self._import_event_rules(
                    pipeline.id, item.get("event_rules", []), steps_data, new_steps
                )
                imported += 1

            except Exception as e:
                errors.append(f"Error importing pipeline {pipeline_id}: {e}")

        return ImportConfirmResponse(
            imported=imported,
            skipped=skipped,
            errors=errors,
        )

    async def _import_event_rules(
        self,
        pipeline_id: str,
        event_rules_data: list[dict],
        steps_data: list[dict],
        new_steps: list[PipelineStep],
    ) -> None:
        """Import event rules, mapping old step IDs to newly created ones.

        new_steps must be the exact list returned by replace_steps (same order
        as steps_data) so that old→new step ID mapping is correct.
        """
        if not event_rules_data:
            return

        # Delete existing rules for this pipeline
        existing = await self.session.execute(
            select(PipelineEventRule).where(
                PipelineEventRule.pipeline_id == pipeline_id
            )
        )
        for r in existing.scalars().all():
            await self.session.delete(r)
        await self.session.flush()

        # Build map from import step IDs to new step IDs
        # new_steps is in steps_data order (insertion order from replace_steps),
        # so new_steps[i] always corresponds to steps_data[i].
        old_to_new = {}
        for i, sd in enumerate(steps_data):
            old_id = sd.get("id")
            if old_id and i < len(new_steps):
                old_to_new[old_id] = new_steps[i].id

        for rule_data in event_rules_data:
            new_source = old_to_new.get(rule_data.get("source_step_id", ""))
            new_target = old_to_new.get(rule_data.get("target_step_id", ""))
            if new_source and new_target:
                rule = PipelineEventRule(
                    pipeline_id=pipeline_id,
                    event_type=rule_data["event_type"],
                    source_step_id=new_source,
                    target_step_id=new_target,
                    enabled=rule_data.get("enabled", True),
                )
                self.session.add(rule)
        await self.session.flush()

    # ── Event Rule CRUD ─────────────────────────────────────────────

    async def add_event_rule(
        self,
        pipeline_id: str,
        event_type: str,
        source_step_id: str,
        target_step_id: str,
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
