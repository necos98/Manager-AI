"""Issue Queue Service — FIFO event-driven queue for issues.

Listens for ``issue_status_changed → Finished`` events and automatically
dequeues the next pending issue, changes it to ``REASONING``, and calls
``run_issue()`` on it.

Maintains a persistent ``QueueEntry`` registry (DB-backed) so the queue
never loses track of dispatched issues. Membership is tracked exclusively
via ``QueueEntry`` — ``IssueStatus.QUEUED`` is deprecated and no longer
used for queue logic.

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
from app.models.issue import IssueStatus
from app.models.queue_entry import QueueEntry, QueueEntryStatus
from app.services.event_service import BaseNotifier, event_service
from app.services.issue_service import IssueService
from app.services.run_issue_service import run_issue

logger = logging.getLogger(__name__)

issue_queue_service_ref: Optional[IssueQueueService] = None


class IssueQueueService(BaseNotifier):
    """Event listener that auto-starts the next queued issue after one finishes.

    Also serves as QueueRegistryService — provides methods for registering
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

    async def register(self, issue_id: str, project_id: str) -> QueueEntry:
        """Create a new QueueEntry with status ``pending``.

        Assigns ``order`` = max existing order for the project + 1.
        Serialized per-project via ``_get_register_lock`` to prevent
        two concurrent calls from reading the same ``max(order)``.
        """
        async with self._get_register_lock(project_id):
            async with async_session() as session:
                # Determine next order for this project
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

    async def mark_dispatching(self, issue_id: str) -> Optional[QueueEntry]:
        """Mark the pending QueueEntry for ``issue_id`` as ``dispatching``.

        Also sets ``dispatched_at`` to the current timestamp.
        If the entry is already DISPATCHING (e.g. from synchronous marking
        inside ``_dequeue_and_run``), returns it as a no-op.
        Returns the updated entry, or None if no entry exists in any
        active state (PENDING or DISPATCHING).
        """
        async with async_session() as session:
            entry = await self._get_pending_by_issue(session, issue_id)
            if entry is None:
                # Already dispatching? (happens when _dequeue_and_run
                # marks it synchronously before emitting events)
                entry = await self._get_dispatching_by_issue(session, issue_id)
                if entry is None:
                    logger.warning(
                        "No pending or dispatching QueueEntry found for issue %s",
                        issue_id,
                    )
                else:
                    logger.debug(
                        "QueueEntry %s already DISPATCHING — no-op", entry.id,
                    )
                return entry
            entry.status = QueueEntryStatus.DISPATCHING
            entry.dispatched_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info(
                "QueueEntry %s marked DISPATCHING at %s",
                entry.id, entry.dispatched_at,
            )
            return entry

    async def mark_dispatched(self, issue_id: str) -> Optional[QueueEntry]:
        """Mark the QueueEntry for ``issue_id`` as ``dispatched``.

        Supports both DISPATCHING → DISPATCHED (normal issue completion)
        and PENDING → DISPATCHED (manual removal from queue).
        """
        async with async_session() as session:
            entry = await self._get_dispatching_by_issue(session, issue_id)
            if entry is None:
                entry = await self._get_pending_by_issue(session, issue_id)
            if entry is None:
                logger.warning(
                    "No active QueueEntry found for issue %s — already dispatched?",
                    issue_id,
                )
                return None
            entry.status = QueueEntryStatus.DISPATCHED
            await session.commit()
            logger.info("QueueEntry %s marked DISPATCHED", entry.id)
            return entry

    async def mark_failed(
        self, issue_id: str, error_message: str,
    ) -> Optional[QueueEntry]:
        """Mark the active QueueEntry for ``issue_id`` as ``failed``."""
        async with async_session() as session:
            # Try dispatching first, then pending
            entry = await self._get_dispatching_by_issue(session, issue_id)
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
                }
                for e in entries
            ]

    # ------------------------------------------------------------------
    # Startup resume
    # ------------------------------------------------------------------

    async def startup_resume(self) -> None:
        """Scan all projects for pending QueueEntries and auto-start if nothing
        is running.

        Called at application startup to resume processing of issues that were
        QUEUED before shutdown/restart.  Fire-and-forget — failures are logged
        but never crash startup.
        """
        if not self._enabled:
            logger.info("Auto queue processing is disabled — skipping startup_resume")
            return

        try:
            async with async_session() as session:
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
                async with async_session() as sess:
                    issue_service = IssueService(sess)
                    running = await issue_service.list_by_project(
                        project_id,
                        status=IssueStatus.REASONING,
                    )

                if running:
                    logger.info(
                        "startup_resume: project %s has a running issue — skipping",
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
        except Exception:
            logger.warning(
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
    # Queue operations — shared between MCP and REST
    # ------------------------------------------------------------------

    async def add_to_queue(
        self, session: AsyncSession, project_id: str, issue_id: str,
    ) -> dict:
        """Add an issue to the FIFO queue.

        Validates that the issue is in NEW or ACCEPTED status.
        Emits an ``issue_status_changed → Queued`` event so the
        event-based queue listener picks it up and registers a
        ``QueueEntry``.

        Returns ``{id, project_id, status}`` on success.
        Raises ``AppError`` on validation failure.
        """
        from app.models.issue import IssueStatus
        from app.utils.datetime import iso_now

        svc = IssueService(session)
        try:
            issue = await svc.get_for_project(issue_id, project_id)
        except AppError as e:
            raise AppError(str(e))

        allowed = {IssueStatus.NEW.value, IssueStatus.ACCEPTED.value}
        if issue.status not in allowed:
            raise AppError(
                f"Issue must be in NEW or ACCEPTED status to queue, "
                f"got {issue.status}",
            )

        await event_service.emit({
            "type": "issue_status_changed",
            "new_status": IssueStatus.QUEUED.value,
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

    async def remove_from_queue(
        self, session: AsyncSession, project_id: str, issue_id: str,
    ) -> dict:
        """Remove an issue from the FIFO queue.

        Looks up the pending ``QueueEntry``, marks it as dispatched,
        and emits an ``issue_status_changed`` event.

        Returns ``{id, project_id, status}`` on success.
        Raises ``AppError`` if the issue has no pending queue entry.
        """
        from app.utils.datetime import iso_now

        svc = IssueService(session)
        try:
            issue = await svc.get_for_project(issue_id, project_id)
        except AppError as e:
            raise AppError(str(e))

        # Check queue membership via QueueEntry, not Issue.status
        entry = await self.get_pending_entry(issue_id)
        if entry is None:
            raise AppError(
                f"Issue {issue_id} is not in the queue "
                f"(no pending QueueEntry)",
            )

        # Mark QueueEntry as dispatched — issue keeps its original status
        await self.mark_dispatched(issue_id)

        await event_service.emit({
            "type": "issue_status_changed",
            "new_status": issue.status,
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
    async def _get_dispatching_by_issue(
        session, issue_id: str,
    ) -> Optional[QueueEntry]:
        """Find the dispatching QueueEntry for an issue."""
        result = await session.execute(
            select(QueueEntry)
            .where(
                QueueEntry.issue_id == issue_id,
                QueueEntry.status == QueueEntryStatus.DISPATCHING,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    async def notify(self, event: dict) -> None:
        """Called by EventService for every emitted event."""
        if event.get("type") != "issue_status_changed":
            return

        new_status = event.get("new_status")
        project_id = event.get("project_id")
        issue_id = event.get("issue_id")

        if new_status == "Finished" and project_id and self._enabled:
            # Auto-processing: dequeue next pending issue
            asyncio.create_task(self._on_issue_finished(project_id, issue_id))

        elif new_status == "Queued" and project_id and issue_id:
            # Always register the queue entry, regardless of auto-processing state
            asyncio.create_task(self._on_issue_queued(project_id, issue_id))

        elif new_status == "Reasoning" and issue_id and self._enabled:
            # When _dequeue_and_run emits this event, it already marked
            # the QueueEntry as DISPATCHING synchronously. The redundant
            # _on_issue_reasoning → mark_dispatching call below is wasted.
            if event.get("_queue_dispatching_handled"):
                return
            # Mark as dispatching when the issue actually starts
            asyncio.create_task(self._on_issue_reasoning(issue_id))

    async def _on_issue_finished(self, project_id: str, issue_id: str) -> None:
        """Handle a finished issue: mark dispatched + dequeue next."""
        try:
            # Mark this issue's QueueEntry as dispatched
            await self.mark_dispatched(issue_id)
            # Dequeue the next pending issue
            await self._dequeue_and_run(project_id)
        except Exception:
            logger.exception(
                "IssueQueueService failed on finished for project %s", project_id,
            )

    async def _on_issue_queued(self, project_id: str, issue_id: str) -> None:
        """Handle a newly queued issue: register entry + maybe auto-start."""
        try:
            await self.register(issue_id, project_id)
            if self._enabled:
                await self._maybe_auto_start_first(project_id, issue_id)
        except Exception:
            logger.exception(
                "IssueQueueService failed on queued for project %s", project_id,
            )

    async def _on_issue_reasoning(self, issue_id: str) -> None:
        """Handle an issue starting: mark QueueEntry as dispatching."""
        try:
            await self.mark_dispatching(issue_id)
        except Exception:
            logger.exception(
                "IssueQueueService failed marking dispatching for issue %s",
                issue_id,
            )

    async def _dequeue_and_run(self, project_id: str) -> None:
        """Find the next pending QueueEntry and start the issue."""
        lock = self._dequeue_locks.setdefault(project_id, asyncio.Lock())
        async with lock:
            try:
                next_entry = await self.get_next_pending(project_id)
                if next_entry is None:
                    logger.debug(
                        "No pending queue entries for project %s — nothing to dequeue",
                        project_id,
                    )
                    return

                logger.info(
                    "Dequeuing issue %s (order=%d) for project %s",
                    next_entry.issue_id, next_entry.order, project_id,
                )

                # ★ Mark as DISPATCHING synchronously BEFORE update_status/emit
                # This closes the race window: a second _on_issue_finished call
                # won't find this entry as PENDING anymore.
                await self.mark_dispatching(next_entry.issue_id)

                async with async_session() as session:
                    issue_service = IssueService(session)

                    # Change status from current (NEW or ACCEPTED) to REASONING.
                    # QueueEntry is the authoritative record — Issue.status no longer
                    # goes through QUEUED.
                    await issue_service.update_status(
                        next_entry.issue_id, project_id, IssueStatus.REASONING,
                    )
                    await session.commit()

                    # Emit status changed event for the transition
                    # (_on_issue_reasoning → mark_dispatching is now a no-op
                    #  because we already marked it synchronously above)
                    from app.mcp.shared_tools import _emit_event
                    from app.utils.datetime import iso_now

                    # Fetch issue name for the event
                    issue = await issue_service.get_for_project(
                        next_entry.issue_id, project_id,
                    )
                    await _emit_event({
                        "type": "issue_status_changed",
                        "new_status": IssueStatus.REASONING.value,
                        "project_id": project_id,
                        "issue_id": next_entry.issue_id,
                        "issue_name": issue.name or "",
                        "timestamp": iso_now(),
                        "_queue_dispatching_handled": True,
                    })

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
                    else:
                        logger.info(
                            "Started queued issue %s — terminal %s",
                            next_entry.issue_id, result.get("term_id"),
                        )
            except Exception:
                logger.exception(
                    "IssueQueueService failed to dequeue for project %s",
                    project_id,
                )

    async def _maybe_auto_start_first(
        self, project_id: str, issue_id: str,
    ) -> None:
        """Auto-start the first QUEUED issue if no issues are currently running.

        This handles the case where the queue was empty and the first
        issue is being added — there's no FINISHED event to trigger
        dequeue, so we start immediately.
        """
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

                # Check if any issue is currently running for this project
                running = await issue_service.list_by_project(
                    project_id,
                    status=IssueStatus.REASONING,
                )

                if not running:
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


# ── Standalone helpers (fallback when IssueQueueService is None) ──────────


async def _queue_add_direct(
    session: AsyncSession, project_id: str, issue_id: str,
) -> dict:
    """Add an issue to the FIFO queue without requiring IssueQueueService.

    Fallback used when issue_queue_service_ref is None (IssueQueueService
    was not initialized during startup). Validates the issue, creates the
    QueueEntry directly, and emits the event for other listeners.

    Returns {id, project_id, status} on success.
    Raises AppError on validation failure.
    """
    from app.models.issue import IssueStatus
    from app.utils.datetime import iso_now

    svc = IssueService(session)
    try:
        issue = await svc.get_for_project(issue_id, project_id)
    except AppError as e:
        raise AppError(str(e))

    allowed = {IssueStatus.NEW.value, IssueStatus.ACCEPTED.value}
    if issue.status not in allowed:
        raise AppError(
            f"Issue must be in NEW or ACCEPTED status to queue, "
            f"got {issue.status}",
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
        "type": "issue_status_changed",
        "new_status": IssueStatus.QUEUED.value,
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


async def _queue_remove_direct(
    session: AsyncSession, project_id: str, issue_id: str,
) -> dict:
    """Remove an issue from the FIFO queue without requiring IssueQueueService.

    Fallback used when issue_queue_service_ref is None (IssueQueueService
    was not initialized during startup). Looks up the pending QueueEntry,
    marks it as dispatched, and emits the event.

    Returns {id, project_id, status} on success.
    Raises AppError if the issue has no pending queue entry.
    """
    from app.utils.datetime import iso_now

    svc = IssueService(session)
    try:
        issue = await svc.get_for_project(issue_id, project_id)
    except AppError as e:
        raise AppError(str(e))

    # Find the pending QueueEntry
    result = await session.execute(
        select(QueueEntry)
        .where(
            QueueEntry.issue_id == issue_id,
            QueueEntry.status == QueueEntryStatus.PENDING,
        )
        .order_by(QueueEntry.order.asc())
        .limit(1)
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise AppError(
            f"Issue {issue_id} is not in the queue (no pending QueueEntry)",
        )

    # Mark as dispatched
    entry.status = QueueEntryStatus.DISPATCHED
    await session.commit()

    # Emit event for other listeners
    await event_service.emit({
        "type": "issue_status_changed",
        "new_status": issue.status,
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
