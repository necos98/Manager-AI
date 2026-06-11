"""Issue Queue Service -- FIFO event-driven queue for issues.

Status-independent: the queue tracks its own state (RUNNING/DONE/STALLED)
via ``QueueEntry`` and does NOT modify ``IssueStatus``. It reacts to
``issue_status_changed -&gt; Finished`` events to mark entries DONE and
advance the queue.

Terminal liveness is checked via ``TerminalService.list_active()`` to
detect stalled entries (terminal died without issue finishing).

Membership is tracked exclusively via ``QueueEntry``.
Registered as a BaseNotifier on EventService at startup in main.py.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func as sa_func

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.exceptions import AppError
from app.models.queue_entry import QueueEntry, QueueEntryStatus
from app.services.event_service import BaseNotifier, event_service
from app.services.issue_service import IssueService
from app.services.run_issue_service import run_issue

logger = logging.getLogger(__name__)

issue_queue_service_ref: Optional[IssueQueueService] = None


class IssueQueueService(BaseNotifier):
    """Event listener that auto-starts the next queued issue after one finishes.

    Also serves as QueueRegistryService -- provides methods for registering
    and tracking queue entries in the persistent ``queue_entries`` table.
    """

    def __init__(self) -> None:
        self._dequeue_locks: dict[str, asyncio.Lock] = {}
        self._register_locks: dict[str, asyncio.Lock] = {}
        self._enabled = False
        event_service.register(self)
        global issue_queue_service_ref
        issue_queue_service_ref = self
        logger.info("IssueQueueService registered on EventService")

    # ------------------------------------------------------------------
    # Lock helpers
    # ------------------------------------------------------------------

    def _get_register_lock(self, project_id: str) -> asyncio.Lock:
        """Get or create a per-project lock for serializing register() calls."""
        if project_id not in self._register_locks:
            self._register_locks[project_id] = asyncio.Lock()
        return self._register_locks[project_id]

    # ------------------------------------------------------------------
    # QueueRegistryService methods
    # ------------------------------------------------------------------

    async def register(self, issue_id: str, project_id: str, skip_if_exists: bool = False) -> QueueEntry:
        """Create a new QueueEntry with status ``pending``.

        Assigns ``order`` = max existing order for the project + 1.
        Serialized per-project via ``_get_register_lock`` to prevent
        two concurrent calls from reading the same ``max(order)``.

        When ``skip_if_exists=True``, returns the existing entry silently
        instead of raising ``AppError`` (used by event handlers for
        idempotent re-registration).
        """
        async with self._get_register_lock(project_id):
            async with async_session() as session:
                existing = await session.execute(
                    select(QueueEntry)
                    .where(
                        QueueEntry.issue_id == issue_id,
                        QueueEntry.status.in_([
                            QueueEntryStatus.PENDING,
                            QueueEntryStatus.RUNNING,
                        ]),
                    )
                    .limit(1)
                )
                existing_entry = existing.scalar_one_or_none()
                if existing_entry is not None:
                    if skip_if_exists:
                        return existing_entry
                    raise AppError(
                        f"Issue {issue_id} is already in the queue "
                        f"(pending or running)",
                    )

                result = await session.execute(
                    select(sa_func.coalesce(sa_func.max(QueueEntry.order), 0))
                    .where(QueueEntry.project_id == project_id)
                )
                max_order: int = result.scalar() or 0

                entry = QueueEntry(
                    issue_id=issue_id,
                    project_id=project_id,
                    status=QueueEntryStatus.PENDING,
                    order=max_order + 1,
                )
                session.add(entry)
                await session.commit()
                logger.info(
                    "QueueEntry registered: issue=%s project=%s order=%s",
                    issue_id, project_id, entry.order,
                )
                return entry

    async def mark_running(
        self, issue_id: str, terminal_id: str,
    ) -> Optional[QueueEntry]:
        """Mark a PENDING QueueEntry as RUNNING and record the terminal_id."""
        async with async_session() as session:
            entry = await self._get_pending_by_issue(session, issue_id)
            if entry is None:
                logger.warning(
                    "No pending QueueEntry found for issue %s to mark running",
                    issue_id,
                )
                return None
            entry.status = QueueEntryStatus.RUNNING
            entry.last_terminal_id = terminal_id
            entry.dispatched_at = datetime.now(timezone.utc)
            entry.status_changed_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info(
                "QueueEntry %s marked RUNNING (terminal=%s)", entry.id, terminal_id,
            )
            return entry

    async def mark_done(self, issue_id: str) -> Optional[QueueEntry]:
        """Mark a RUNNING or PENDING QueueEntry as DONE."""
        async with async_session() as session:
            entry = await self._find_running_entry(session, issue_id)
            if entry is None:
                entry = await self._get_pending_by_issue(session, issue_id)
            if entry is None:
                logger.warning(
                    "No active QueueEntry found for issue %s to mark done",
                    issue_id,
                )
                return None
            entry.status = QueueEntryStatus.DONE
            entry.status_changed_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info("QueueEntry %s marked DONE", entry.id)
            return entry

    async def mark_stalled(self, issue_id: str) -> Optional[QueueEntry]:
        """Mark a RUNNING QueueEntry as STALLED (terminal died without FINISHED)."""
        async with async_session() as session:
            entry = await self._find_running_entry(session, issue_id)
            if entry is None:
                logger.warning(
                    "No RUNNING QueueEntry found for issue %s to mark stalled",
                    issue_id,
                )
                return None
            entry.status = QueueEntryStatus.STALLED
            entry.status_changed_at = datetime.now(timezone.utc)
            await session.commit()
            logger.warning("QueueEntry %s marked STALLED", entry.id)
            return entry

    async def mark_failed(
        self, issue_id: str, error_message: str,
    ) -> Optional[QueueEntry]:
        """Mark a RUNNING or PENDING QueueEntry as FAILED."""
        async with async_session() as session:
            entry = await self._find_running_entry(session, issue_id)
            if entry is None:
                entry = await self._get_pending_by_issue(session, issue_id)
            if entry is None:
                logger.warning(
                    "No active QueueEntry found for issue %s to mark failed",
                    issue_id,
                )
                return None
            entry.status = QueueEntryStatus.FAILED
            entry.error_message = error_message[:1000]
            entry.status_changed_at = datetime.now(timezone.utc)
            await session.commit()
            logger.error(
                "QueueEntry %s marked FAILED: %s", entry.id, error_message,
            )
            return entry

    async def get_next_pending(self, project_id: str) -> Optional[QueueEntry]:
        """Get the next pending QueueEntry for a project, ordered by ``order`` ASC.

        Returns the entry with the lowest ``order`` that is still ``pending``.
        """
        async with async_session() as session:
            result = await session.execute(
                select(QueueEntry)
                .where(
                    QueueEntry.project_id == project_id,
                    QueueEntry.status == QueueEntryStatus.PENDING,
                )
                .order_by(QueueEntry.order.asc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def list_queue(self, project_id: str) -> list[dict]:
        """List all QueueEntries for a project, ordered by ``order`` ASC.

        Returns a list of dicts for MCP tool serialisation.
        """
        async with async_session() as session:
            result = await session.execute(
                select(QueueEntry)
                .where(QueueEntry.project_id == project_id)
                .order_by(QueueEntry.order.asc())
            )
            entries = result.scalars().all()
            return [
                {
                    "id": e.id,
                    "issue_id": e.issue_id,
                    "project_id": e.project_id,
                    "status": e.status.value,
                    "order": e.order,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "dispatched_at": e.dispatched_at.isoformat() if e.dispatched_at else None,
                    "error_message": e.error_message,
                    "last_terminal_id": e.last_terminal_id,
                    "retry_count": e.retry_count,
                }
                for e in entries
            ]

    async def list_all_global(self) -> list[dict]:
        """List all QueueEntries across all projects, ordered by ``order`` ASC."""
        async with async_session() as session:
            result = await session.execute(
                select(QueueEntry).order_by(QueueEntry.order.asc())
            )
            entries = result.scalars().all()
            return [
                {
                    "id": e.id,
                    "issue_id": e.issue_id,
                    "project_id": e.project_id,
                    "status": e.status.value,
                    "order": e.order,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "dispatched_at": e.dispatched_at.isoformat() if e.dispatched_at else None,
                    "error_message": e.error_message,
                    "last_terminal_id": e.last_terminal_id,
                    "retry_count": e.retry_count,
                }
                for e in entries
            ]

    # ------------------------------------------------------------------
    # Startup resume
    # ------------------------------------------------------------------

    async def startup_resume(self) -> None:
        """Scan all projects for pending QueueEntries and auto-start if nothing
        is running.

        Also detects STALLED entries: RUNNING QueueEntries whose terminal
        is no longer active (server restart). These are re-queued as PENDING
        so they get retried.

        Called at application startup. Fire-and-forget -- failures are logged
        but never crash startup.
        """
        if not self._enabled:
            logger.info("Auto queue processing is disabled -- skipping startup_resume")
            return

        try:
            from app.services.terminal_service import terminal_service

            async with async_session() as session:
                # Mark RUNNING entries without active terminal as STALLED
                running_result = await session.execute(
                    select(QueueEntry)
                    .where(QueueEntry.status == QueueEntryStatus.RUNNING)
                )
                for entry in running_result.scalars().all():
                    active_terms = terminal_service.list_active(
                        project_id=entry.project_id, issue_id=entry.issue_id,
                    )
                    if not active_terms:
                        entry.status = QueueEntryStatus.STALLED
                        entry.status_changed_at = datetime.now(timezone.utc)
                        logger.warning(
                            "QueueEntry %s marked STALLED at startup (no active terminal)",
                            entry.id,
                        )
                        # Retry: re-queue as PENDING (skip if already re-queued)
                        await self.register(entry.issue_id, entry.project_id, skip_if_exists=True)
                await session.commit()

                # Find projects with PENDING entries to auto-start
                result = await session.execute(
                    select(QueueEntry.project_id)
                    .where(QueueEntry.status == QueueEntryStatus.PENDING)
                    .distinct()
                )
                project_ids = [row[0] for row in result.all()]

            if not project_ids:
                logger.debug("startup_resume: no pending queue entries found")
                return

            for project_id in project_ids:
                active_running = await self._count_active_running(project_id)
                if active_running > 0:
                    logger.info(
                        "startup_resume: project %s has a RUNNING entry -- skipping",
                        project_id,
                    )
                    continue

                logger.info(
                    "startup_resume: auto-starting next queued issue for project %s",
                    project_id,
                )
                asyncio.create_task(self._dequeue_and_run(project_id))
        except Exception:
            logger.exception("IssueQueueService.startup_resume failed")

    # ------------------------------------------------------------------
    # Runtime toggle
    # ------------------------------------------------------------------

    async def load_state(self) -> None:
        """Load the ``queue_auto_process`` setting from DB into ``self._enabled``.

        Called at startup after construction.  Defaults to ``False`` if
        the setting cannot be read.
        """
        try:
            async with async_session() as session:
                from app.services.settings_service import SettingsService
                svc = SettingsService(session)
                val = await svc.get("queue_auto_process")
                self._enabled = val.lower() == "true"
        except KeyError:
            self._enabled = False
        except Exception:
            logger.exception(
                "Failed to load queue_auto_process setting; defaulting to disabled",
            )
            self._enabled = False

    async def set_enabled(self, enabled: bool) -> None:
        """Persist the toggle state and (if enabling) attempt to resume
        queue processing."""
        self._enabled = enabled
        async with async_session() as session:
            from app.services.settings_service import SettingsService
            svc = SettingsService(session)
            await svc.set("queue_auto_process", "true" if enabled else "false")
            await session.commit()
        logger.info("Queue auto-processing %s", "enabled" if enabled else "disabled")
        if enabled:
            asyncio.create_task(self.startup_resume())

    # ------------------------------------------------------------------
    # Queue operations -- shared between MCP and REST
    # ------------------------------------------------------------------

    async def add_to_queue(
        self, session: AsyncSession, project_id: str, issue_id: str,
    ) -> dict:
        """Add an issue to the FIFO queue.

        Raises ``AppError`` if the issue is already in the queue
        (has a PENDING or RUNNING QueueEntry).
        """
        from app.utils.datetime import iso_now

        svc = IssueService(session)
        try:
            issue = await svc.get_for_project(issue_id, project_id)
        except AppError as e:
            raise AppError(str(e))

        # Register synchronously so QueueEntry exists when response returns.
        # No status validation -- any issue can be queued.
        await self.register(issue_id, project_id)

        await event_service.emit({
            "type": "queue_entry_created",
            "project_id": project_id,
            "issue_id": issue_id,
            "issue_name": issue.name or "",
            "timestamp": iso_now(),
        })

        # Auto-start is handled by the event-driven _on_issue_queued path
        # (triggered by the queue_entry_created event emitted above)

        return {
            "id": issue_id,
            "project_id": project_id,
            "status": issue.status,
        }

    async def remove_from_queue(
        self, session: AsyncSession, project_id: str, issue_id: str,
        force: bool = False,
    ) -> dict:
        """Remove an issue from the FIFO queue.

        Hard-deletes the QueueEntry record. When ``force=True``, also
        kills the terminal for RUNNING entries before deleting.
        Emits a ``queue_entry_removed`` event.

        Returns ``{id, project_id, status}`` on success.
        Raises ``AppError`` if the issue has no queue entry or is RUNNING
        without ``force``.
        """
        from app.utils.datetime import iso_now

        svc = IssueService(session)
        try:
            issue = await svc.get_for_project(issue_id, project_id)
        except AppError as e:
            raise AppError(str(e))

        # Delete any active QueueEntry (PENDING or RUNNING)
        async with async_session() as s:
            result = await s.execute(
                select(QueueEntry).where(
                    QueueEntry.issue_id == issue_id,
                    QueueEntry.status.in_([
                        QueueEntryStatus.PENDING,
                        QueueEntryStatus.RUNNING,
                    ]),
                ).limit(1)
            )
            entry = result.scalar_one_or_none()

            if entry is None:
                raise AppError(
                    f"Issue {issue_id} is not in the queue",
                )

            if entry.status == QueueEntryStatus.RUNNING and not force:
                raise AppError(
                    f"Issue {issue_id} is currently RUNNING. "
                    f"Use force=true to stop and remove it.",
                )

            # Kill terminal only if entry is actually RUNNING
            if force and entry.status == QueueEntryStatus.RUNNING:
                from app.services.terminal_service import terminal_service
                active_terms = terminal_service.list_active(
                    project_id=project_id, issue_id=issue_id,
                )
                for term in active_terms:
                    terminal_service.kill(term["id"])

            await s.delete(entry)
            await s.commit()
            logger.info(
                "QueueEntry %s deleted for issue %s", entry.id, issue_id,
            )

        await event_service.emit({
            "type": "queue_entry_removed",
            "project_id": project_id,
            "issue_id": issue_id,
            "issue_name": issue.name or "",
            "timestamp": iso_now(),
        })

        return {
            "id": issue_id,
            "project_id": project_id,
            "status": issue.status,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def get_pending_entry(self, issue_id: str) -> Optional[QueueEntry]:
        """Get the pending QueueEntry for an issue, if any.

        Returns None if the issue has no pending queue entry.
        """
        async with async_session() as session:
            return await self._get_pending_by_issue(session, issue_id)

    @staticmethod
    async def _get_pending_by_issue(
        session, issue_id: str,
    ) -> Optional[QueueEntry]:
        """Find the pending QueueEntry for an issue (lowest order)."""
        result = await session.execute(
            select(QueueEntry)
            .where(
                QueueEntry.issue_id == issue_id,
                QueueEntry.status == QueueEntryStatus.PENDING,
            )
            .order_by(QueueEntry.order.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _find_running_entry(
        session, issue_id: str,
    ) -> Optional[QueueEntry]:
        """Find the RUNNING QueueEntry for an issue."""
        result = await session.execute(
            select(QueueEntry)
            .where(
                QueueEntry.issue_id == issue_id,
                QueueEntry.status == QueueEntryStatus.RUNNING,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _count_active_running(self, project_id: str) -> int:
        """Count QueueEntry in RUNNING state for this project.

        Does NOT look at IssueStatus -- the queue is status-independent.
        """
        async with async_session() as session:
            result = await session.execute(
                select(sa_func.count(QueueEntry.id))
                .where(
                    QueueEntry.project_id == project_id,
                    QueueEntry.status == QueueEntryStatus.RUNNING,
                )
            )
            return result.scalar() or 0

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    async def notify(self, event: dict) -> None:
        """Called by EventService for every emitted event."""
        event_type = event.get("type")
        project_id = event.get("project_id")
        issue_id = event.get("issue_id")

        if event_type == "queue_entry_created" and project_id and issue_id:
            asyncio.create_task(self._on_issue_queued(project_id, issue_id))
            return

        if event_type != "issue_status_changed":
            return

        new_status = event.get("new_status")

        if new_status == "Finished" and project_id and issue_id and self._enabled:
            asyncio.create_task(self._on_issue_finished(project_id, issue_id))

    async def _on_issue_finished(self, project_id: str, issue_id: str) -> None:
        """Issue FINISHED -&gt; find RUNNING QueueEntry -&gt; mark DONE -&gt; dequeue next."""
        try:
            done = await self.mark_done(issue_id)
            if done is None:
                logger.warning(
                    "Issue %s finished but no RUNNING QueueEntry found "
                    "(finished outside the queue?)", issue_id,
                )
            await self._dequeue_and_run(project_id)
        except Exception:
            logger.exception(
                "IssueQueueService failed on finished for project %s", project_id,
            )

    async def _on_issue_queued(self, project_id: str, issue_id: str) -> None:
        """Handle a newly queued issue: ensure entry exists + maybe auto-start.

        Registration is idempotent via ``skip_if_exists=True`` -- silently
        returns existing entry if already registered (e.g., from synchronous
        register() in add_to_queue).
        Auto-starts if no RUNNING entry exists for this project.
        """
        try:
            await self.register(issue_id, project_id, skip_if_exists=True)
            if self._enabled:
                await self._maybe_auto_start_first(project_id, issue_id)
        except Exception:
            logger.exception(
                "IssueQueueService failed on queued for project %s", project_id,
            )

    async def _dequeue_and_run(self, project_id: str) -> None:
        """Find the next PENDING QueueEntry and start the issue. Does NOT modify IssueStatus. Tracks state via QueueEntry (RUNNING). Saves the terminal_id from run_issue() for liveness checks."""
        lock = self._dequeue_locks.setdefault(project_id, asyncio.Lock())
        async with lock:
            next_entry = None
            try:
                next_entry = await self.get_next_pending(project_id)
                if next_entry is None:
                    logger.debug(
                        "No pending queue entries for project %s -- nothing to dequeue",
                        project_id,
                    )
                    return

                logger.info(
                    "Dequeuing issue %s (order=%d) for project %s",
                    next_entry.issue_id, next_entry.order, project_id,
                )

                async with async_session() as session:
                    # Start the issue via run_issue
                    logger.info(
                        "Starting run_issue for issue %s", next_entry.issue_id,
                    )
                    result = await run_issue(
                        issue_id=next_entry.issue_id,
                        project_id=project_id,
                        session=session,
                    )
                    if "error" in result:
                        logger.error(
                            "Failed to start queued issue %s: %s",
                            next_entry.issue_id, result["error"],
                        )
                        await self.mark_failed(
                            next_entry.issue_id, result["error"],
                        )
                        return

                    terminal_id = result.get("term_id", "")
                    await self.mark_running(next_entry.issue_id, terminal_id)
                    logger.info(
                        "Started queued issue %s -- terminal %s",
                        next_entry.issue_id, terminal_id,
                    )
            except Exception:
                logger.exception(
                    "IssueQueueService failed to dequeue for project %s",
                    project_id,
                )
                if next_entry is not None:
                    await self.mark_failed(
                        next_entry.issue_id,
                        "Exception in _dequeue_and_run",
                    )

    async def _maybe_auto_start_first(
        self, project_id: str, issue_id: str,
    ) -> None:
        """Auto-start the first queued issue if no issues are currently running. When queue was empty and first issue is added, start it immediately since no FINISHED event will trigger dequeue."""
        try:
            async with async_session() as session:
                issue_service = IssueService(session)

                # Count how many pending QueueEntries exist for this project
                result = await session.execute(
                    select(sa_func.count(QueueEntry.id))
                    .where(
                        QueueEntry.project_id == project_id,
                        QueueEntry.status == QueueEntryStatus.PENDING,
                    )
                )
                pending_count: int = result.scalar() or 0

                # Only auto-start if there's at least one pending entry
                if pending_count < 1:
                    return

                # Check if any QueueEntry is RUNNING for this project
                active_running = await self._count_active_running(project_id)
                if active_running == 0:
                    logger.info(
                        "Auto-starting first queued issue %s for project %s",
                        issue_id, project_id,
                    )
                    await self._dequeue_and_run(project_id)
        except Exception:
            logger.exception(
                "IssueQueueService failed in _maybe_auto_start_first for project %s",
                project_id,
            )


# -- Standalone helpers (fallback when IssueQueueService is None) ----------


async def _queue_add_direct(
    session: AsyncSession, project_id: str, issue_id: str,
) -> dict:
    """Add an issue to the FIFO queue without requiring IssueQueueService.

    Fallback used when issue_queue_service_ref is None (IssueQueueService
    was not initialized during startup). Creates the QueueEntry directly
    and emits the event. No status validation -- any issue can be queued.

    Returns {id, project_id, status} on success.
    """
    from app.utils.datetime import iso_now

    svc = IssueService(session)
    try:
        issue = await svc.get_for_project(issue_id, project_id)
    except AppError as e:
        raise AppError(str(e))

    # Check for existing active entry (duplicate prevention)
    existing = await session.execute(
        select(QueueEntry)
        .where(
            QueueEntry.issue_id == issue_id,
            QueueEntry.status.in_([
                QueueEntryStatus.PENDING,
                QueueEntryStatus.RUNNING,
            ]),
        )
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        raise AppError(
            f"Issue {issue_id} is already in the queue "
            f"(pending or running)",
        )

    # Create QueueEntry directly (same logic as IssueQueueService.register())
    result = await session.execute(
        select(sa_func.coalesce(sa_func.max(QueueEntry.order), 0))
        .where(QueueEntry.project_id == project_id)
    )
    max_order: int = result.scalar() or 0

    entry = QueueEntry(
        issue_id=issue_id,
        project_id=project_id,
        status=QueueEntryStatus.PENDING,
        order=max_order + 1,
    )
    session.add(entry)
    await session.commit()

    # Emit event for any other listeners (also logged by NotificationService)
    await event_service.emit({
        "type": "queue_entry_created",
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue.name or "",
        "timestamp": iso_now(),
    })

    # If the queue service is now available and auto-process is enabled,
    # attempt to auto-start the first pending issue
    if issue_queue_service_ref and issue_queue_service_ref._enabled:
        await issue_queue_service_ref._maybe_auto_start_first(project_id, issue_id)

    return {
        "id": issue_id,
        "project_id": project_id,
        "status": issue.status,
    }


async def _queue_remove_direct(
    session: AsyncSession, project_id: str, issue_id: str,
    force: bool = False,
) -> dict:
    """Remove an issue from the FIFO queue without requiring IssueQueueService.

    Fallback used when issue_queue_service_ref is None. Hard-deletes the
    QueueEntry record. When ``force=True``, also kills the terminal.

    Returns {id, project_id, status} on success.
    Raises AppError if the issue has no queue entry or is RUNNING without force.
    """
    from app.utils.datetime import iso_now

    svc = IssueService(session)
    try:
        issue = await svc.get_for_project(issue_id, project_id)
    except AppError as e:
        raise AppError(str(e))

    # Find and delete any active QueueEntry (PENDING or RUNNING)
    result = await session.execute(
        select(QueueEntry).where(
            QueueEntry.issue_id == issue_id,
            QueueEntry.status.in_([
                QueueEntryStatus.PENDING,
                QueueEntryStatus.RUNNING,
            ]),
        ).limit(1)
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise AppError(
            f"Issue {issue_id} is not in the queue",
        )

    if entry.status == QueueEntryStatus.RUNNING and not force:
        raise AppError(
            f"Issue {issue_id} is currently RUNNING. "
            f"Use force=true to stop and remove it.",
        )

    # Kill terminal only if entry is actually RUNNING
    if force and entry.status == QueueEntryStatus.RUNNING:
        from app.services.terminal_service import terminal_service
        active_terms = terminal_service.list_active(
            project_id=project_id, issue_id=issue_id,
        )
        for term in active_terms:
            terminal_service.kill(term["id"])

    await session.delete(entry)
    await session.commit()

    # Emit event for other listeners
    await event_service.emit({
        "type": "queue_entry_removed",
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue.name or "",
        "timestamp": iso_now(),
    })

    return {
        "id": issue_id,
        "project_id": project_id,
        "status": issue.status,
    }
