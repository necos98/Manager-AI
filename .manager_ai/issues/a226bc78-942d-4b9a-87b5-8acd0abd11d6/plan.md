# Implementation Plan: PipelineRunService + TaskManager + ArtifactService

## Files Map

| Action | File | Responsibility |
|---|---|---|
| Create | `backend/app/schemas/pipeline_run.py` | Pydantic request/response schemas |
| Modify | `backend/app/schemas/__init__.py` | Export new schemas |
| Create | `backend/app/services/artifact_service.py` | Read/write/list artifacts files |
| Create | `backend/app/services/pipeline_task_manager.py` | asyncio.Task registry singleton |
| Create | `backend/app/services/pipeline_run_service.py` | Pipeline execution orchestrator |
| Create | `backend/app/routers/pipeline_runs.py` | REST endpoints for pipeline runs |
| Modify | `backend/app/main.py` | Register pipeline_runs router + startup cleanup |
| Create | `backend/tests/test_pipeline_run_service.py` | Tests for the orchestrator |

---

### Task 1: Pydantic schemas for pipeline runs

**Files:**
- Create: `backend/app/schemas/pipeline_run.py`
- Modify: `backend/app/schemas/__init__.py`

Schemas:
```python
from datetime import datetime
from pydantic import BaseModel, Field

class PipelineRunStart(BaseModel):
    pipeline_id: str = Field(..., min_length=1)
    issue_id: str = Field(..., min_length=1)

class PipelineStepRunResponse(BaseModel):
    id: str
    pipeline_run_id: str
    pipeline_step_id: str
    agent_name: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None

class PipelineRunResponse(BaseModel):
    id: str
    pipeline_id: str
    issue_id: str
    status: str
    current_step_index: int
    steps: list[PipelineStepRunResponse] = []
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str | None = None

class PipelineMessageCreate(BaseModel):
    sender_agent_name: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)

class PipelineMessageResponse(BaseModel):
    id: str
    pipeline_run_id: str
    sender_agent_name: str
    content: str
    created_at: str | None = None
```

Update `__init__.py` to export new schemas.

---

### Task 2: ArtifactService

**Files:**
- Create: `backend/app/services/artifact_service.py`

```python
import os
from pathlib import Path

from app.exceptions import NotFoundError

class ArtifactService:
    @staticmethod
    def _artifacts_dir(project_path: str, issue_id: str) -> Path:
        return Path(project_path) / ".manager_ai" / "issues" / issue_id / "artifacts"

    @staticmethod
    def save_artifact(project_path: str, issue_id: str, filename: str, content: str) -> str:
        dir_path = ArtifactService._artifacts_dir(project_path, issue_id)
        dir_path.mkdir(parents=True, exist_ok=True)
        filepath = dir_path / filename
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    @staticmethod
    def read_artifact(project_path: str, issue_id: str, filename: str) -> str:
        filepath = ArtifactService._artifacts_dir(project_path, issue_id) / filename
        if not filepath.exists():
            raise NotFoundError(f"Artifact not found: {filename}")
        return filepath.read_text(encoding="utf-8")

    @staticmethod
    def list_artifacts(project_path: str, issue_id: str) -> list[str]:
        dir_path = ArtifactService._artifacts_dir(project_path, issue_id)
        if not dir_path.exists():
            return []
        return sorted([f.name for f in dir_path.iterdir() if f.is_file()])
```

---

### Task 3: PipelineTaskManager

**Files:**
- Create: `backend/app/services/pipeline_task_manager.py`

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

class PipelineTaskManager:
    def __init__(self):
        self._registry: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_task(self, run_id: str, task: asyncio.Task) -> None:
        async with self._lock:
            self._registry[run_id] = task

    async def cancel_task(self, run_id: str) -> None:
        async with self._lock:
            task = self._registry.get(run_id)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self.cleanup_task(run_id)

    async def cleanup_task(self, run_id: str) -> None:
        async with self._lock:
            self._registry.pop(run_id, None)

    def get_task(self, run_id: str) -> asyncio.Task | None:
        return self._registry.get(run_id)

    def active_runs(self) -> list[str]:
        return list(self._registry.keys())

pipeline_task_manager = PipelineTaskManager()
```

---

### Task 4: PipelineRunService

**Files:**
- Create: `backend/app/services/pipeline_run_service.py`

Core orchestrator. Dependencies: AsyncSession, TerminalService, PipelineTaskManager.

```python
import asyncio
import logging
import os
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.models.agent import Agent
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineMessage, PipelineRun, PipelineRunStatus,
    PipelineStepRun, PipelineStepRunStatus,
)
from app.services.artifact_service import ArtifactService
from app.services.pipeline_task_manager import pipeline_task_manager
from app.services.terminal_service import terminal_service

logger = logging.getLogger(__name__)

DEFAULT_STEP_TIMEOUT = int(os.environ.get("MANAGER_AI_PIPELINE_STEP_TIMEOUT", "1800"))

class PipelineRunService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start(self, pipeline_id: str, issue_id: str, project_id: str, project_path: str) -> dict:
        # Check no active run for this issue
        existing = await self.session.execute(
            select(PipelineRun).where(
                PipelineRun.issue_id == issue_id,
                PipelineRun.status == PipelineRunStatus.RUNNING,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValidationError(f"A pipeline is already running for issue {issue_id}")

        pipeline = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.id == pipeline_id)
            .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
        )
        pipeline = pipeline.unique().scalar_one_or_none()
        if pipeline is None:
            raise NotFoundError(f"Pipeline not found: {pipeline_id}")

        run = PipelineRun(
            pipeline_id=pipeline_id,
            issue_id=issue_id,
            status=PipelineRunStatus.RUNNING,
            current_step_index=0,
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        await self.session.flush()

        step_responses = []
        for step in sorted(pipeline.steps, key=lambda s: s.order_index):
            step_run = PipelineStepRun(
                pipeline_run_id=run.id,
                pipeline_step_id=step.id,
                status=PipelineStepRunStatus.PENDING,
            )
            self.session.add(step_run)
            await self.session.flush()
            step_responses.append({
                "id": step_run.id,
                "pipeline_run_id": run.id,
                "pipeline_step_id": step.id,
                "agent_name": step.agent.name if step.agent else "unknown",
                "status": PipelineStepRunStatus.PENDING.value,
            })

        task = asyncio.create_task(self._execute(run.id, project_id, project_path))
        await pipeline_task_manager.start_task(run.id, task)

        return {
            "id": run.id,
            "pipeline_id": run.pipeline_id,
            "issue_id": run.issue_id,
            "status": run.status.value,
            "current_step_index": run.current_step_index,
            "steps": step_responses,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": None,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    async def _execute(self, run_id: str, project_id: str, project_path: str) -> None:
        run = await self._get_run(run_id)
        pipeline = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.id == run.pipeline_id)
            .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
        )
        pipeline = pipeline.unique().scalar_one_or_none()
        if pipeline is None:
            return

        steps = sorted(pipeline.steps, key=lambda s: s.order_index)

        for i, step in enumerate(steps):
            step_run_result = await self.session.execute(
                select(PipelineStepRun).where(
                    PipelineStepRun.pipeline_run_id == run_id,
                    PipelineStepRun.pipeline_step_id == step.id,
                )
            )
            step_run = step_run_result.scalar_one_or_none()
            if step_run is None:
                continue

            step_run.status = PipelineStepRunStatus.RUNNING
            step_run.started_at = datetime.now(timezone.utc)
            run.current_step_index = i
            await self.session.flush()

            agent = step.agent
            agent_name = agent.name if agent else "unknown"
            agent_prompt = agent.system_prompt if agent else ""

            # Resolve command variables
            cmd = step.terminal_command or ""
            cmd = cmd.replace("$issue_id", run.issue_id)
            cmd = cmd.replace("$project_id", project_id)
            cmd = cmd.replace("$project_path", project_path)

            # Create log terminal for streaming output
            term = await terminal_service.create_log(
                project_id=project_id,
                issue_id=run.issue_id,
                project_path=project_path,
                label=f"{agent_name} (step {i+1}/{len(steps)})",
            )
            term_id = term["id"]
            step_run.terminal_id = int(term_id) if term_id.isdigit() else None
            await self.session.flush()

            try:
                success = await self._run_step(
                    term_id=term_id,
                    agent_name=agent_name,
                    system_prompt=agent_prompt,
                    command=cmd,
                    project_path=project_path,
                    run_id=run_id,
                    issue_id=run.issue_id,
                )

                if success:
                    step_run.status = PipelineStepRunStatus.COMPLETED
                else:
                    step_run.status = PipelineStepRunStatus.FAILED
                    run.status = PipelineRunStatus.FAILED
                    step_run.finished_at = datetime.now(timezone.utc)
                    await self.session.flush()
                    await terminal_service.destroy_log(term_id)
                    break

                step_run.finished_at = datetime.now(timezone.utc)
                await self.session.flush()
            except Exception as e:
                logger.exception("Step %s failed with exception", agent_name)
                step_run.status = PipelineStepRunStatus.FAILED
                run.status = PipelineRunStatus.FAILED
                step_run.finished_at = datetime.now(timezone.utc)
                await self.session.flush()
                await terminal_service.destroy_log(term_id)
                break

            await terminal_service.destroy_log(term_id)

        # Mark run completed if all steps succeeded
        await self.session.refresh(run)
        if run.status != PipelineRunStatus.FAILED:
            run.status = PipelineRunStatus.COMPLETED
        run.finished_at = datetime.now(timezone.utc)
        await self.session.flush()
        await pipeline_task_manager.cleanup_task(run_id)

    async def _run_step(self, term_id: str, agent_name: str, system_prompt: str, command: str, project_path: str, run_id: str, issue_id: str) -> bool:
        full_cmd = f'claude -p "System prompt: {system_prompt}\\n\\nTask: {command}\\n\\nIssue ID: {issue_id}\\nPipeline run ID: {run_id}"'

        env = os.environ.copy()
        env["MANAGER_AI_AGENT_NAME"] = agent_name
        env["MANAGER_AI_AGENT_ROLE"] = agent_name

        proc = await asyncio.create_subprocess_shell(
            full_cmd,
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )

        async def stream_output():
            if proc.stdout is None:
                return
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                await terminal_service.push_output(term_id, text)

        stream_task = asyncio.create_task(stream_output())

        try:
            exit_code = await asyncio.wait_for(proc.wait(), timeout=DEFAULT_STEP_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            stream_task.cancel()
            return False

        await stream_task
        return exit_code == 0

    async def _get_run(self, run_id: str) -> PipelineRun:
        result = await self.session.execute(
            select(PipelineRun)
            .where(PipelineRun.id == run_id)
            .options(
                selectinload(PipelineRun.step_runs).selectinload(PipelineStepRun.pipeline_step).selectinload(PipelineStep.agent)
            )
        )
        run = result.unique().scalar_one_or_none()
        if run is None:
            raise NotFoundError(f"Pipeline run not found: {run_id}")
        return run

    async def get_run(self, run_id: str) -> dict:
        run = await self._get_run(run_id)
        steps = []
        for sr in sorted(run.step_runs, key=lambda s: s.pipeline_step.order_index if s.pipeline_step else 0):
            agent_name = "unknown"
            if sr.pipeline_step and sr.pipeline_step.agent:
                agent_name = sr.pipeline_step.agent.name
            steps.append({
                "id": sr.id,
                "pipeline_run_id": sr.pipeline_run_id,
                "pipeline_step_id": sr.pipeline_step_id,
                "agent_name": agent_name,
                "status": sr.status.value,
                "started_at": sr.started_at.isoformat() if sr.started_at else None,
                "finished_at": sr.finished_at.isoformat() if sr.finished_at else None,
            })
        return {
            "id": run.id,
            "pipeline_id": run.pipeline_id,
            "issue_id": run.issue_id,
            "status": run.status.value,
            "current_step_index": run.current_step_index,
            "steps": steps,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    async def get_runs_for_issue(self, issue_id: str) -> list[dict]:
        result = await self.session.execute(
            select(PipelineRun)
            .where(PipelineRun.issue_id == issue_id)
            .options(selectinload(PipelineRun.step_runs))
            .order_by(PipelineRun.created_at.desc())
        )
        runs = result.unique().scalars().all()
        return [
            {
                "id": r.id,
                "pipeline_id": r.pipeline_id,
                "issue_id": r.issue_id,
                "status": r.status.value,
                "current_step_index": r.current_step_index,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]

    async def cancel_run(self, run_id: str) -> bool:
        run = await self._get_run(run_id)
        if run.status != PipelineRunStatus.RUNNING:
            raise ValidationError("Can only cancel running pipelines")
        await pipeline_task_manager.cancel_task(run_id)
        run.status = PipelineRunStatus.FAILED
        run.finished_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def add_message(self, run_id: str, sender_agent_name: str, content: str) -> dict:
        msg = PipelineMessage(
            pipeline_run_id=run_id,
            sender_agent_name=sender_agent_name,
            content=content,
        )
        self.session.add(msg)
        await self.session.flush()
        return {
            "id": msg.id,
            "pipeline_run_id": msg.pipeline_run_id,
            "sender_agent_name": msg.sender_agent_name,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }

    async def get_messages(self, run_id: str) -> list[dict]:
        result = await self.session.execute(
            select(PipelineMessage)
            .where(PipelineMessage.pipeline_run_id == run_id)
            .order_by(PipelineMessage.created_at)
        )
        msgs = result.scalars().all()
        return [
            {
                "id": m.id,
                "pipeline_run_id": m.pipeline_run_id,
                "sender_agent_name": m.sender_agent_name,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ]
```

---

### Task 5: REST router for pipeline runs

**Files:**
- Create: `backend/app/routers/pipeline_runs.py`

Prefix: `/api/projects/{project_id}/pipeline-runs`

Endpoints:
- `POST /` — start pipeline run
- `GET /` — list runs for issue (?issue_id=X)
- `GET /{run_id}` — get run status
- `DELETE /{run_id}` — cancel run
- `GET /{run_id}/messages` — get chat messages
- `POST /{run_id}/messages` — send chat message

Router follows same pattern as `backend/app/routers/pipelines.py`: Depends(get_db) for AsyncSession, instantiate PipelineRunService, await methods, db.commit() after mutations.

---

### Task 6: Wire up in main.py

**Files:**
- Modify: `backend/app/main.py`

Changes:
1. Add import: `from app.routers import pipeline_runs`
2. Register router: `app.include_router(pipeline_runs.router)`
3. Add startup cleanup in lifespan: query RUNNING PipelineRuns and mark them FAILED (server restart orphan cleanup)

---

### Task 7: Startup cleanup

In `main.py` lifespan, after the existing seed block, add:

```python
# Mark orphaned pipeline runs as FAILED (server restart)
try:
    from app.models.pipeline_run import PipelineRun, PipelineRunStatus
    async with async_session() as cleanup_session:
        orphaned = await cleanup_session.execute(
            select(PipelineRun).where(PipelineRun.status == PipelineRunStatus.RUNNING)
        )
        for run in orphaned.scalars().all():
            run.status = PipelineRunStatus.FAILED
            run.finished_at = datetime.now(timezone.utc)
        await cleanup_session.commit()
except Exception:
    logger.exception("Failed to cleanup orphaned pipeline runs")
```

---

### Task 8: Test orchestrator

**Files:**
- Create: `backend/tests/test_pipeline_run_service.py`

Tests:
- `test_start_creates_run_and_step_runs` — verify PipelineRun + PipelineStepRuns created
- `test_start_rejects_double_start` — verify ValidationError on duplicate
- `test_get_run_returns_status` — verify status response shape
- `test_add_and_get_messages` — verify message round-trip
- `test_cancel_run` — verify cancel sets FAILED
- `test_cancel_non_running_raises` — verify ValidationError
- `test_get_runs_for_issue` — verify filtered listing

---

## Execution Order

1. Schemas + __init__.py update
2. ArtifactService (no dependencies)
3. PipelineTaskManager (no dependencies)
4. PipelineRunService (depends on 2, 3)
5. Router (depends on 1, 4)
6. main.py wire-up (depends on 5)
7. Startup cleanup (depends on 6)
8. Tests (depends on 1-7)
