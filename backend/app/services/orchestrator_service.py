"""OrchestratorService: manages agent pipeline execution for issues."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.hooks.executor import ClaudeCodeExecutor
from app.models.agent import Agent
from app.models.agent_message import AgentMessage
from app.models.issue import Issue, IssueStatus
from app.models.pipeline import AgentStepRun, AgentStepStatus, Pipeline, PipelineRun, PipelineRunStatus
from app.services.event_service import event_service
from app.services.project_service import ProjectService
from app.services.terminal_service import terminal_service

logger = logging.getLogger(__name__)


class OrchestratorService:
    """Manages agent pipeline lifecycle: start, step execution, completion."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.executor = ClaudeCodeExecutor()

    DEFAULT_AGENTS = [
        {
            "name": "SpecWriter",
            "role_key": "spec_writer",
            "system_prompt": (
                "You are a Technical Specification Writer. Your job is to analyze issue requirements "
                "and produce a clear, detailed specification and implementation plan.\n\n"
                "## Workflow\n"
                "1. Read the issue description carefully\n"
                "2. Call `create_issue_spec` to write the specification (moves issue NEW → REASONING)\n"
                "3. Call `create_issue_plan` to write the implementation plan (moves REASONING → PLANNED)\n"
                "4. Call `create_plan_tasks` to break the plan into atomic tasks\n"
                "5. Call `send_agent_message` with type='decision' summarizing key architectural choices\n"
                "6. Call `complete_agent_step` with a summary of what you produced\n\n"
                "## Guidelines\n"
                "- Specs should be detailed, covering architecture, data flow, edge cases\n"
                "- Plans should be actionable with specific files, functions, and patterns\n"
                "- Tasks should be atomic (1-2 files each) and ordered by dependency\n"
                "- Communicate decisions to the next agents via send_agent_message"
            ),
        },
        {
            "name": "Architect",
            "role_key": "architect",
            "system_prompt": (
                "You are a Software Architect. Analyze requirements, design system architecture, "
                "and write technical specifications. Output concise, actionable specs. "
                "When done, call complete_agent_step with your architectural decisions."
            ),
        },
        {
            "name": "Developer",
            "role_key": "developer",
            "system_prompt": (
                "You are a Senior Developer. Implement code following the specification. "
                "Write tests. Keep code clean and follow existing patterns. "
                "When done, call complete_agent_step with implementation summary."
            ),
        },
        {
            "name": "Reviewer",
            "role_key": "reviewer",
            "system_prompt": (
                "You are a Code Reviewer. Review the implementation for bugs, security issues, "
                "and code quality. Check adherence to spec. "
                "When done, call complete_agent_step with review findings."
            ),
        },
        {
            "name": "QA",
            "role_key": "qa",
            "system_prompt": (
                "You are a QA Engineer. Verify the implementation meets requirements. "
                "Run tests, check edge cases, validate acceptance criteria. "
                "When done, call complete_agent_step with test results."
            ),
        },
    ]

    async def ensure_default_agents(self, project_id: str) -> list[Agent]:
        """Create default agents if none exist for the project. Idempotent."""
        result = await self.session.execute(
            select(func.count()).select_from(Agent).where(Agent.project_id == project_id)
        )
        count = result.scalar() or 0
        if count > 0:
            result = await self.session.execute(
                select(Agent).where(Agent.project_id == project_id).order_by(Agent.name)
            )
            return list(result.scalars().all())

        agents = []
        for data in self.DEFAULT_AGENTS:
            agent = Agent(
                project_id=project_id,
                name=data["name"],
                role_key=data["role_key"],
                system_prompt=data["system_prompt"],
            )
            self.session.add(agent)
            agents.append(agent)
        await self.session.commit()
        return agents

    async def ensure_default_pipeline(self, project_id: str) -> Pipeline | None:
        """Create default pipeline if none exist for the project. Idempotent.

        Requires agents to exist first (call ensure_default_agents before this).
        """
        result = await self.session.execute(
            select(func.count()).select_from(Pipeline).where(Pipeline.project_id == project_id)
        )
        count = result.scalar() or 0
        if count > 0:
            result = await self.session.execute(
                select(Pipeline).where(
                    Pipeline.project_id == project_id,
                    Pipeline.is_default == True,
                )
            )
            return result.scalar_one_or_none()

        agents_result = await self.session.execute(
            select(Agent).where(Agent.project_id == project_id).order_by(Agent.name)
        )
        agents = agents_result.scalars().all()
        if not agents:
            return None

        role_order = ["spec_writer", "architect", "developer", "reviewer", "qa"]
        steps = []
        for i, role_key in enumerate(role_order):
            agent = next((a for a in agents if a.role_key == role_key), None)
            if agent:
                steps.append({"agent_id": agent.id, "order": i})

        pipeline = Pipeline(
            project_id=project_id,
            name="Default",
            steps=json.dumps(steps),
            is_default=True,
            trigger_type="issue_accepted",
        )
        self.session.add(pipeline)
        await self.session.commit()
        return pipeline

    async def start_pipeline(
        self,
        trigger_type: str = "issue_accepted",
        issue_id: str | None = None,
        project_id: str | None = None,
        issue_status: str | None = None,
    ) -> PipelineRun | None:
        """Create PipelineRun + AgentStepRuns and begin background execution.

        Returns the PipelineRun immediately. Pipeline executes asynchronously.
        Supports starting from any issue state by skipping already-completed steps.

        Callers SHOULD pass project_id + issue_status to avoid a DB lookup
        (issues are stored on disk, not in the SQLAlchemy issue table).
        """
        if not issue_id:
            logger.warning("start_pipeline requires issue_id")
            return None

        if project_id and issue_status is not None:
            # Issue resolved from file store — ensure shadow DB row for FK constraints
            issue = await self.session.get(Issue, issue_id)
            if issue is None:
                issue = Issue(
                    id=issue_id,
                    project_id=project_id,
                    description="",
                    status=IssueStatus(issue_status),
                )
                self.session.add(issue)
                await self.session.flush()
        else:
            issue = await self.session.get(Issue, issue_id)
            if issue is None:
                logger.warning("Issue %s not found, cannot start pipeline", issue_id)
                return None
            project_id = issue.project_id
            issue_status = issue.status.value if hasattr(issue.status, 'value') else str(issue.status)

        # Prevent duplicate runs
        existing = await self.session.execute(
            select(PipelineRun).where(
                PipelineRun.issue_id == issue_id,
                PipelineRun.status == PipelineRunStatus.RUNNING,
            )
        )
        if existing.scalar_one_or_none() is not None:
            logger.info("Pipeline already running for issue %s", issue_id)
            return None

        pipeline = await self._get_default_pipeline(project_id)
        if pipeline is None:
            logger.info("No default pipeline for project %s", project_id)
            return None

        steps = json.loads(pipeline.steps) if pipeline.steps else []
        if not steps:
            logger.info("Pipeline %s has no steps", pipeline.id)
            return None

        # Determine starting step based on issue state
        start_idx = self._get_starting_step_index(issue_status=issue_status)

        pipeline_run = PipelineRun(
            pipeline_id=pipeline.id,
            issue_id=issue_id,
            trigger_type=trigger_type,
            status=PipelineRunStatus.RUNNING,
        )
        self.session.add(pipeline_run)
        await self.session.flush()

        for i, step_def in enumerate(steps):
            if i < start_idx:
                logger.debug("Skipping step %d (%s) — already covered by issue state", i, step_def.get("agent_role", ""))
                continue

            agent = await self.session.get(Agent, step_def.get("agent_id", ""))
            if agent is None:
                result = await self.session.execute(
                    select(Agent).where(
                        Agent.project_id == project_id,
                        Agent.role_key == step_def.get("agent_role", ""),
                        Agent.enabled == True,
                    )
                )
                agent = result.scalar_one_or_none()
            if agent is None:
                logger.warning("Agent not found for step %s", step_def)
                continue

            step_run = AgentStepRun(
                pipeline_run_id=pipeline_run.id,
                agent_id=agent.id,
                agent_name=agent.name,
                agent_role=agent.role_key,
                step_order=i,
                status=AgentStepStatus.PENDING,
            )
            self.session.add(step_run)

        await self.session.commit()
        await self.session.refresh(pipeline_run)

        asyncio.create_task(self._run_pipeline(pipeline_run))
        return pipeline_run

    ROLE_ORDER = ["spec_writer", "architect", "developer", "reviewer", "qa"]

    def _get_starting_step_index(self, issue: Issue | None = None, issue_status: str | None = None) -> int:
        """Determine which step to start from based on issue state.

        - NEW: start from spec_writer (index 0)
        - REASONING: skip spec_writer, start from architect (index 1)
        - PLANNED/ACCEPTED: skip spec_writer+architect, start from developer (index 2)
        """
        status = issue_status
        if issue is not None:
            status = issue.status.value if hasattr(issue.status, 'value') else str(issue.status)
        if status in ("Planned", "Accepted"):
            return 2
        elif status == "Reasoning":
            return 1
        else:
            return 0

    async def _get_default_pipeline(self, project_id: str) -> Pipeline | None:
        result = await self.session.execute(
            select(Pipeline).where(
                Pipeline.project_id == project_id,
                Pipeline.is_default == True,
            )
        )
        return result.scalar_one_or_none()

    async def _run_pipeline(self, pipeline_run: PipelineRun) -> None:
        """Execute steps sequentially. Each step spawns a Claude Code subprocess."""
        pipeline = await self.session.get(Pipeline, pipeline_run.pipeline_id)
        project_id = pipeline.project_id if pipeline else ""

        pipeline_run.status = PipelineRunStatus.RUNNING
        await self._commit()

        steps = await self._get_step_runs(pipeline_run.id)

        for step in steps:
            success = await self._run_agent_step(pipeline_run, step, project_id=project_id)
            if not success:
                pipeline_run.status = PipelineRunStatus.PAUSED
                pipeline_run.completed_at = datetime.now(timezone.utc)
                await self._commit()
                await self._emit("pipeline_paused", pipeline_run, project_id=project_id)
                return

        pipeline_run.status = PipelineRunStatus.COMPLETED
        pipeline_run.completed_at = datetime.now(timezone.utc)
        await self._commit()
        await self._emit("pipeline_completed", pipeline_run, project_id=project_id)

    async def _run_agent_step(
        self, pipeline_run: PipelineRun, step: AgentStepRun, *, project_id: str = ""
    ) -> bool:
        agent = await self.session.get(Agent, step.agent_id)
        if agent is None or not agent.enabled:
            step.status = AgentStepStatus.FAILED
            step.error = "Agent not found or disabled"
            await self._commit()
            return False

        resolved_project_id = project_id or agent.project_id

        project = await ProjectService(self.session).get_by_id(agent.project_id)
        issue = (
            await self.session.get(Issue, pipeline_run.issue_id)
            if pipeline_run.issue_id
            else None
        )

        step.status = AgentStepStatus.RUNNING
        step.started_at = datetime.now(timezone.utc)
        await self._commit()

        await self._emit("agent_step_started", pipeline_run, step, project_id=resolved_project_id)

        project_path = project.path if project else ""
        log_term = await terminal_service.create_log(
            project_id=resolved_project_id,
            issue_id=pipeline_run.issue_id or "",
            project_path=project_path,
            label=agent.name,
        )
        step.terminal_id = log_term["id"]
        await self._commit()

        await self._emit("agent_terminal_created", pipeline_run, step, project_id=resolved_project_id)

        prompt = self._build_prompt(agent, issue, pipeline_run)

        async def on_output(text: str) -> None:
            await terminal_service.push_output(log_term["id"], text)

        result = await self.executor.run_streaming(
            prompt=prompt,
            project_path=project_path,
            env_vars={
                "MANAGER_AI_PROJECT_ID": agent.project_id,
                "MANAGER_AI_AGENT_NAME": agent.name,
                "MANAGER_AI_AGENT_ROLE": agent.role_key,
            },
            on_output=on_output,
        )

        await terminal_service.destroy_log(log_term["id"])

        await self.session.refresh(step)

        if step.status == AgentStepStatus.COMPLETED:
            await self._emit("agent_step_completed", pipeline_run, step, project_id=resolved_project_id)
            return True

        step.status = AgentStepStatus.FAILED
        step.error = result.error or f"Exit code non-zero"
        step.completed_at = datetime.now(timezone.utc)
        await self._commit()
        await self._emit("agent_step_failed", pipeline_run, step, project_id=resolved_project_id)
        return False

    def _build_prompt(
        self, agent: Agent, issue: Issue | None, pipeline_run: PipelineRun
    ) -> str:
        parts = [agent.system_prompt or f"You are the {agent.name} agent."]

        parts.append(
            f"\n## Pipeline Info\n"
            f"Pipeline run ID: {pipeline_run.id}\n"
            f"Agent: {agent.name} ({agent.role_key})"
        )

        if issue:
            parts.append(f"\n## Issue: {issue.name or '(unnamed)'}")
            parts.append(f"Description: {issue.description}")
            if issue.specification:
                parts.append(f"\n### Specification\n{issue.specification}")
            if issue.plan:
                parts.append(f"\n### Plan\n{issue.plan}")

        parts.append(
            "\n## Communication\n"
            "Use `send_agent_message` to write to the agent chat.\n"
            "Use `get_agent_messages` to read chat history.\n"
            "When your work is complete, call `complete_agent_step` with a summary."
        )

        return "\n".join(parts)

    async def complete_agent_step(self, pipeline_run_id: str, summary: str = "") -> dict:
        """Mark the current running step as completed."""
        result = await self.session.execute(
            select(AgentStepRun)
            .where(
                AgentStepRun.pipeline_run_id == pipeline_run_id,
                AgentStepRun.status == AgentStepStatus.RUNNING,
            )
            .order_by(AgentStepRun.step_order)
            .limit(1)
        )
        step = result.scalar_one_or_none()
        if step is None:
            return {"error": "No running step found for this pipeline run"}

        step.status = AgentStepStatus.COMPLETED
        step.summary = summary
        step.completed_at = datetime.now(timezone.utc)
        await self._commit()
        return {
            "completed": True,
            "step_id": step.id,
            "agent_name": step.agent_name,
            "agent_role": step.agent_role,
        }

    async def get_pipeline_status(self, pipeline_run_id: str) -> dict:
        """Return full pipeline state with all step statuses."""
        pipeline_run = await self.session.get(PipelineRun, pipeline_run_id)
        if pipeline_run is None:
            return {"error": "Pipeline run not found"}

        steps = await self._get_step_runs(pipeline_run_id)

        return {
            "pipeline_run": {
                "id": pipeline_run.id,
                "pipeline_id": pipeline_run.pipeline_id,
                "issue_id": pipeline_run.issue_id,
                "trigger_type": pipeline_run.trigger_type,
                "status": pipeline_run.status.value,
                "started_at": pipeline_run.started_at.isoformat() if pipeline_run.started_at else None,
                "completed_at": pipeline_run.completed_at.isoformat() if pipeline_run.completed_at else None,
            },
            "steps": [
                {
                    "id": s.id,
                    "agent_id": s.agent_id,
                    "agent_name": s.agent_name,
                    "agent_role": s.agent_role,
                    "step_order": s.step_order,
                    "status": s.status.value,
                    "summary": s.summary,
                    "error": s.error,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                }
                for s in steps
            ],
        }

    async def _get_step_runs(self, pipeline_run_id: str) -> list[AgentStepRun]:
        result = await self.session.execute(
            select(AgentStepRun)
            .where(AgentStepRun.pipeline_run_id == pipeline_run_id)
            .order_by(AgentStepRun.step_order)
        )
        return list(result.scalars().all())

    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except Exception as exc:
            logger.error("Orchestrator commit failed: %s", exc)
            await self.session.rollback()

    async def _emit(
        self, event_type: str, pipeline_run: PipelineRun, step: AgentStepRun | None = None, *, project_id: str
    ) -> None:
        try:
            payload: dict = {
                "type": event_type,
                "project_id": project_id,
                "pipeline_run_id": pipeline_run.id,
                "issue_id": pipeline_run.issue_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if step:
                payload.update({
                    "step_id": step.id,
                    "agent_name": step.agent_name,
                    "agent_role": step.agent_role,
                    "step_order": step.step_order,
                })
                if step.terminal_id:
                    payload["terminal_id"] = step.terminal_id
                if event_type == "agent_step_completed":
                    payload["summary"] = step.summary
                elif event_type == "agent_step_failed":
                    payload["error"] = step.error
            await event_service.emit(payload)
        except Exception as exc:
            logger.warning("Failed to emit pipeline event: %s", exc)
