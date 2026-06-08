"""PipelineRunService facade -- delegates to specialized sub-modules.

This is the ONLY public entry point. All external callers import from here
via the package __init__.py.

Every public method delegates cleanly to a sub-module. Adding a new feature
means adding a new _<feature>.py module and wiring it here -- no file
grows beyond ~200 lines.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline_run import (
    _execution,
    _lifecycle,
    _messages,
    _orchestrated,
    _queries,
    _rejection,
)


class PipelineRunService:
    """Facade for pipeline run operations."""

    def __init__(self, session: AsyncSession, session_factory=None):
        self.session = session
        self.session_factory = session_factory

    # ── Lifecycle ────────────────────────────────────────────────

    async def start(
        self, pipeline_id: str, issue_id: str, project_id: str, project_path: str,
        orchestrated: bool = False,
    ) -> dict:
        return await _lifecycle.start(
            pipeline_id, issue_id, project_id, project_path,
            orchestrated, self.session, self.session_factory,
        )

    async def pause_run(self, run_id: str) -> dict:
        return await _lifecycle.pause_run(run_id, self.session)

    async def resume_run(self, run_id: str) -> dict:
        return await _lifecycle.resume_run(run_id, self.session)

    async def cancel_run(self, run_id: str) -> bool:
        return await _lifecycle.cancel_run(run_id, self.session)

    async def advance_step(self, run_id: str) -> dict:
        return await _lifecycle.advance_step(run_id, self.session)

    # ── Orchestrated execution ──────────────────────────────────

    async def start_step(
        self, run_id: str, project_id: str, project_path: str,
    ) -> dict:
        return await _orchestrated.start_step(
            run_id, project_id, project_path, self.session,
        )

    # ── Rejection ───────────────────────────────────────────────

    async def resolve_rejection_target(
        self, run_id: str, step_id: str,
    ) -> int | None:
        return await _rejection.resolve_rejection_target(
            run_id, step_id, self.session,
        )

    async def reject_step(
        self, run_id: str, reason: str, target_step_index: int, project_id: str,
    ) -> dict:
        return await _rejection.reject_step(
            run_id, reason, target_step_index, project_id, self.session,
        )

    # ── Queries ─────────────────────────────────────────────────

    async def get_run(self, run_id: str) -> dict:
        return await _queries.get_run(run_id, self.session)

    async def get_runs_for_issue(self, issue_id: str) -> list[dict]:
        return await _queries.get_runs_for_issue(issue_id, self.session)

    async def get_active_runs_for_issues(
        self, issue_ids: list[str],
    ) -> dict[str, dict | None]:
        return await _queries.get_active_runs_for_issues(issue_ids, self.session)

    async def get_active_runs_for_project(self, project_id: str) -> list[dict]:
        return await _queries.get_active_runs_for_project(project_id, self.session)

    # ── Messages ────────────────────────────────────────────────

    async def add_message(
        self, run_id: str, sender_agent_name: str, content: str,
    ) -> dict:
        return await _messages.add_message(
            run_id, sender_agent_name, content, self.session,
        )

    async def get_messages(self, run_id: str) -> list[dict]:
        return await _messages.get_messages(run_id, self.session)
