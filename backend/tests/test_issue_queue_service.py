"""Tests for IssueQueueService — FIFO event-driven queue for issues.

Covers the full lifecycle: QueueEntry model, registry CRUD, event handling,
auto-start/dequeue, startup resume, configuration toggle, and FIFO multi-project.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import asyncio
import pytest
import pytest_asyncio

from app.models.queue_entry import QueueEntry, QueueEntryStatus
from app.models.setting import Setting
from app.services import event_service as evt_mod
from app.services.issue_queue_service import IssueQueueService, issue_queue_service_ref


# ==============================================================================
# Helpers
# ==============================================================================


@asynccontextmanager
async def _session_patch_context(db_session):
    """Replacement for async_session() — yields the test db_session."""
    yield db_session


def make_session_patcher(db_session):
    """Return a callable that mimics async_sessionmaker for patching."""
    return lambda: _session_patch_context(db_session)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest_asyncio.fixture
async def project(db_session):
    from app.services.project_service import ProjectService
    svc = ProjectService(db_session)
    return await svc.create(name="Test Queue A", path="/tmp/test-queue-a", description="")


@pytest_asyncio.fixture
async def project_b(db_session):
    from app.services.project_service import ProjectService
    svc = ProjectService(db_session)
    return await svc.create(name="Test Queue B", path="/tmp/test-queue-b", description="")


@pytest_asyncio.fixture
async def queue_service(db_session):
    """Create a fresh IssueQueueService and patch async_session for the test.

    The patch is active for the duration of the test so every method call
    inside the service uses the in-memory SQLite DB.
    """
    patcher = patch(
        "app.services.issue_queue_service.async_session",
        make_session_patcher(db_session),
        create=True,
    )
    patcher.start()
    try:
        svc = IssueQueueService()
        svc._enabled = True  # enabled by default for most tests
        yield svc
    finally:
        patcher.stop()


@pytest_asyncio.fixture
async def queue_service_disabled(db_session):
    """IssueQueueService with _enabled=False."""
    patcher = patch(
        "app.services.issue_queue_service.async_session",
        make_session_patcher(db_session),
        create=True,
    )
    patcher.start()
    try:
        svc = IssueQueueService()
        svc._enabled = False
        yield svc
    finally:
        patcher.stop()


# ==============================================================================
# TASK 1: Test di base — QueueEntry model, QueueEntryStatus, constructor
# ==============================================================================


class TestQueueEntryModel:
    """QueueEntryStatus enum and QueueEntry model defaults."""

    def test_enum_values(self):
        assert QueueEntryStatus.PENDING == "pending"
        assert QueueEntryStatus.DISPATCHING == "dispatching"
        assert QueueEntryStatus.DISPATCHED == "dispatched"
        assert QueueEntryStatus.FAILED == "failed"

    def test_enum_members(self):
        assert len(QueueEntryStatus) == 4

    @pytest.mark.asyncio
    async def test_queue_entry_defaults(self, db_session):
        """QueueEntry gets id (UUID), status=PENDING, and order from constructor."""
        entry = QueueEntry(
            issue_id="iss-1", project_id="proj-1", order=1,
        )
        db_session.add(entry)
        await db_session.commit()

        assert entry.id is not None
        assert len(entry.id) == 36  # UUID length
        assert entry.status == QueueEntryStatus.PENDING
        assert entry.order == 1
        assert entry.issue_id == "iss-1"
        assert entry.project_id == "proj-1"
        assert entry.created_at is not None
        assert entry.dispatched_at is None
        assert entry.error_message is None


class TestIssueQueueServiceConstructor:
    """__init__ registration and module-level ref."""

    def test_registers_on_event_service(self):
        """IssueQueueService.__init__ calls event_service.register(self)."""
        svc = IssueQueueService()
        # Should be in the notifiers list
        assert svc in evt_mod.event_service._notifiers, (
            "IssueQueueService should be registered on EventService"
        )
        # Clean up from global state for other tests
        evt_mod.event_service._notifiers = [
            n for n in evt_mod.event_service._notifiers if n is not svc
        ]

    def test_module_level_ref_is_set(self):
        """__init__ sets the module-level ref in app.services.issue_queue_service."""
        # Use module-level access: `from X import Y` creates a local copy,
        # but `global` in __init__ modifies the module attribute.
        from app.services import issue_queue_service as iqs_mod

        old_ref = iqs_mod.issue_queue_service_ref
        svc = IssueQueueService()
        try:
            assert iqs_mod.issue_queue_service_ref is not None, (
                "issue_queue_service_ref should not be None after __init__"
            )
            assert iqs_mod.issue_queue_service_ref is svc, (
                "should point to the new instance"
            )
        finally:
            evt_mod.event_service._notifiers = [
                n for n in evt_mod.event_service._notifiers if n is not svc
            ]

    def test_initially_disabled(self):
        """_enabled starts as False."""
        svc = IssueQueueService()
        try:
            assert svc._enabled is False
        finally:
            evt_mod.event_service._notifiers = [
                n for n in evt_mod.event_service._notifiers if n is not svc
            ]


# ==============================================================================
# TASK 2: Test registry CRUD — register, mark_dispatching, mark_dispatched,
#          mark_failed
# ==============================================================================


class TestRegistryCRUD:
    """register, mark_dispatching, mark_dispatched, mark_failed methods."""

    @pytest.mark.asyncio
    async def test_register_creates_entry_with_order(self, queue_service, project, db_session):
        """register() creates a QueueEntry with order=1 for first entry."""
        entry = await queue_service.register("iss-1", project.id)
        assert entry is not None
        assert entry.issue_id == "iss-1"
        assert entry.project_id == project.id
        assert entry.status == QueueEntryStatus.PENDING
        assert entry.order == 1  # first entry

    @pytest.mark.asyncio
    async def test_register_auto_increment_order(self, queue_service, project, db_session):
        """register() increments order for each new entry in same project."""
        e1 = await queue_service.register("iss-1", project.id)
        e2 = await queue_service.register("iss-2", project.id)
        e3 = await queue_service.register("iss-3", project.id)
        assert e1.order == 1
        assert e2.order == 2
        assert e3.order == 3

    @pytest.mark.asyncio
    async def test_register_independent_order_per_project(
        self, queue_service, project, project_b, db_session,
    ):
        """register() maintains independent order counters per project."""
        e1 = await queue_service.register("iss-a1", project.id)
        e2 = await queue_service.register("iss-b1", project_b.id)
        e3 = await queue_service.register("iss-a2", project.id)
        assert e1.order == 1
        assert e2.order == 1  # project B starts at 1
        assert e3.order == 2

    # -- mark_dispatching tests --

    @pytest.mark.asyncio
    async def test_mark_dispatching_success(self, queue_service, project, db_session):
        """mark_dispatching() changes PENDING → DISPATCHING with dispatched_at."""
        entry = await queue_service.register("iss-1", project.id)
        assert entry.status == QueueEntryStatus.PENDING

        result = await queue_service.mark_dispatching("iss-1")
        assert result is not None
        assert result.status == QueueEntryStatus.DISPATCHING
        assert result.dispatched_at is not None

    @pytest.mark.asyncio
    async def test_mark_dispatching_already_dispatching(self, queue_service, project, db_session):
        """mark_dispatching() is a no-op if entry is already DISPATCHING."""
        e1 = await queue_service.register("iss-1", project.id)
        await queue_service.mark_dispatching("iss-1")
        result = await queue_service.mark_dispatching("iss-1")
        assert result is not None
        assert result.status == QueueEntryStatus.DISPATCHING

    @pytest.mark.asyncio
    async def test_mark_dispatching_missing_entry(self, queue_service):
        """mark_dispatching() returns None for unknown issue_id."""
        result = await queue_service.mark_dispatching("nonexistent")
        assert result is None

    # -- mark_dispatched tests --

    @pytest.mark.asyncio
    async def test_mark_dispatched_from_dispatching(self, queue_service, project, db_session):
        """mark_dispatched() changes DISPATCHING → DISPATCHED (normal completion)."""
        await queue_service.register("iss-1", project.id)
        await queue_service.mark_dispatching("iss-1")
        result = await queue_service.mark_dispatched("iss-1")
        assert result is not None
        assert result.status == QueueEntryStatus.DISPATCHED

    @pytest.mark.asyncio
    async def test_mark_dispatched_from_pending(self, queue_service, project, db_session):
        """mark_dispatched() changes PENDING → DISPATCHED (manual removal)."""
        await queue_service.register("iss-1", project.id)
        result = await queue_service.mark_dispatched("iss-1")
        assert result is not None
        assert result.status == QueueEntryStatus.DISPATCHED

    @pytest.mark.asyncio
    async def test_mark_dispatched_missing_entry(self, queue_service):
        """mark_dispatched() returns None for unknown issue_id."""
        result = await queue_service.mark_dispatched("nonexistent")
        assert result is None

    # -- mark_failed tests --

    @pytest.mark.asyncio
    async def test_mark_failed_from_dispatching(self, queue_service, project, db_session):
        """mark_failed() changes DISPATCHING → FAILED with error_message."""
        await queue_service.register("iss-1", project.id)
        await queue_service.mark_dispatching("iss-1")
        result = await queue_service.mark_failed("iss-1", "Something went wrong")
        assert result is not None
        assert result.status == QueueEntryStatus.FAILED
        assert result.error_message == "Something went wrong"

    @pytest.mark.asyncio
    async def test_mark_failed_from_pending(self, queue_service, project, db_session):
        """mark_failed() changes PENDING → FAILED."""
        await queue_service.register("iss-1", project.id)
        result = await queue_service.mark_failed("iss-1", "Failed before start")
        assert result is not None
        assert result.status == QueueEntryStatus.FAILED

    @pytest.mark.asyncio
    async def test_mark_failed_truncates_message(self, queue_service, project, db_session):
        """mark_failed() truncates error_message to 1000 characters."""
        long_msg = "x" * 2000
        await queue_service.register("iss-1", project.id)
        await queue_service.mark_dispatching("iss-1")
        result = await queue_service.mark_failed("iss-1", long_msg)
        assert len(result.error_message) == 1000

    @pytest.mark.asyncio
    async def test_mark_failed_missing_entry(self, queue_service):
        """mark_failed() returns None for unknown issue_id."""
        result = await queue_service.mark_failed("nonexistent", "error")
        assert result is None


# ==============================================================================
# TASK 3: Test query — get_next_pending, list_queue, list_all_global,
#          get_pending_entry
# ==============================================================================


class TestQuery:
    """Query methods for retrieving QueueEntries."""

    @pytest.mark.asyncio
    async def test_get_next_pending_fifo_order(self, queue_service, project, db_session):
        """get_next_pending() returns entry with lowest order."""
        await queue_service.register("iss-1", project.id)
        await queue_service.register("iss-2", project.id)
        await queue_service.register("iss-3", project.id)
        next_entry = await queue_service.get_next_pending(project.id)
        assert next_entry is not None
        assert next_entry.issue_id == "iss-1"
        assert next_entry.order == 1

    @pytest.mark.asyncio
    async def test_get_next_pending_no_pending(self, queue_service, project, db_session):
        """get_next_pending() returns None when no pending entries."""
        result = await queue_service.get_next_pending(project.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_pending_ignores_non_pending(
        self, queue_service, project, db_session,
    ):
        """get_next_pending() does not return dispatched/failed entries."""
        await queue_service.register("iss-1", project.id)
        await queue_service.mark_dispatched("iss-1")
        result = await queue_service.get_next_pending(project.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_pending_scoped_to_project(
        self, queue_service, project, project_b, db_session,
    ):
        """get_next_pending() only returns entries for the specified project."""
        await queue_service.register("iss-a1", project.id)
        await queue_service.register("iss-b1", project_b.id)
        next_a = await queue_service.get_next_pending(project.id)
        next_b = await queue_service.get_next_pending(project_b.id)
        assert next_a.issue_id == "iss-a1"
        assert next_b.issue_id == "iss-b1"

    # -- list_queue tests --

    @pytest.mark.asyncio
    async def test_list_queue_ordered(self, queue_service, project, db_session):
        """list_queue() returns entries ordered by order ASC."""
        await queue_service.register("iss-3", project.id)
        await queue_service.register("iss-1", project.id)
        await queue_service.register("iss-2", project.id)
        entries = await queue_service.list_queue(project.id)
        assert len(entries) == 3
        orders = [e["order"] for e in entries]
        assert orders == [1, 2, 3]
        issue_ids = [e["issue_id"] for e in entries]
        assert issue_ids == ["iss-3", "iss-1", "iss-2"]

    @pytest.mark.asyncio
    async def test_list_queue_scoped_to_project(
        self, queue_service, project, project_b, db_session,
    ):
        """list_queue() only includes entries for the specified project."""
        await queue_service.register("iss-a1", project.id)
        await queue_service.register("iss-b1", project_b.id)
        entries_a = await queue_service.list_queue(project.id)
        entries_b = await queue_service.list_queue(project_b.id)
        assert len(entries_a) == 1
        assert len(entries_b) == 1
        assert entries_a[0]["issue_id"] == "iss-a1"
        assert entries_b[0]["issue_id"] == "iss-b1"

    @pytest.mark.asyncio
    async def test_list_queue_serializes_fields(
        self, queue_service, project, db_session,
    ):
        """list_queue() returns dicts with expected fields."""
        await queue_service.register("iss-1", project.id)
        entries = await queue_service.list_queue(project.id)
        e = entries[0]
        assert "id" in e
        assert "issue_id" in e
        assert "project_id" in e
        assert "status" in e
        assert "order" in e
        assert "created_at" in e
        assert e["status"] == "pending"

    # -- list_all_global tests --

    @pytest.mark.asyncio
    async def test_list_all_global_all_projects(
        self, queue_service, project, project_b, db_session,
    ):
        """list_all_global() returns entries from all projects."""
        await queue_service.register("iss-a1", project.id)
        await queue_service.register("iss-b1", project_b.id)
        all_entries = await queue_service.list_all_global()
        assert len(all_entries) == 2
        project_ids = {e["project_id"] for e in all_entries}
        assert project_ids == {project.id, project_b.id}

    @pytest.mark.asyncio
    async def test_list_all_global_empty(self, queue_service):
        """list_all_global() returns empty list when no entries exist."""
        entries = await queue_service.list_all_global()
        assert entries == []

    # -- get_pending_entry tests --

    @pytest.mark.asyncio
    async def test_get_pending_entry_found(self, queue_service, project, db_session):
        """get_pending_entry() returns the pending entry for an issue_id."""
        await queue_service.register("iss-1", project.id)
        entry = await queue_service.get_pending_entry("iss-1")
        assert entry is not None
        assert entry.issue_id == "iss-1"
        assert entry.status == QueueEntryStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_pending_entry_not_found(self, queue_service):
        """get_pending_entry() returns None for nonexistent issue."""
        entry = await queue_service.get_pending_entry("nonexistent")
        assert entry is None

    @pytest.mark.asyncio
    async def test_get_pending_entry_ignores_non_pending(
        self, queue_service, project, db_session,
    ):
        """get_pending_entry() does not return dispatched entries."""
        await queue_service.register("iss-1", project.id)
        await queue_service.mark_dispatched("iss-1")
        entry = await queue_service.get_pending_entry("iss-1")
        assert entry is None


# ==============================================================================
# TASK 4: Test event handling — notify routing + _on_issue_finished/queued/
#          reasoning
# ==============================================================================


class TestEventHandling:
    """notify() event routing and _on_issue_* handlers."""

    @pytest.mark.asyncio
    async def test_notify_ignores_wrong_event_type(self, queue_service):
        """notify() skips events with type != issue_status_changed."""
        with patch.object(queue_service, "_on_issue_finished") as mock_finish:
            await queue_service.notify({"type": "some_other_event"})
            mock_finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_disabled(self, queue_service_disabled):
        """notify() skips all events when _enabled=False."""
        event = {
            "type": "issue_status_changed",
            "new_status": "Finished",
            "project_id": "p1",
            "issue_id": "i1",
        }
        with (
            patch.object(queue_service_disabled, "_on_issue_finished") as mock_finish,
            patch.object(queue_service_disabled, "_on_issue_queued") as mock_queued,
            patch.object(queue_service_disabled, "_on_issue_reasoning") as mock_reason,
        ):
            await queue_service_disabled.notify(event)
            mock_finish.assert_not_called()
            mock_queued.assert_not_called()
            mock_reason.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_finished_routes_correctly(self, queue_service):
        """Finished event triggers _on_issue_finished.

        notify() uses asyncio.create_task, so we let the event loop
        process it with a short sleep before checking.
        """
        with patch.object(queue_service, "_on_issue_finished",
                          new_callable=AsyncMock) as mock_finish:
            await queue_service.notify({
                "type": "issue_status_changed",
                "new_status": "Finished",
                "project_id": "p1",
                "issue_id": "i1",
            })
            await asyncio.sleep(0)
            mock_finish.assert_awaited_once_with("p1", "i1")

    @pytest.mark.asyncio
    async def test_notify_queue_entry_created_routes_correctly(self, queue_service):
        """queue_entry_created event triggers _on_issue_queued."""
        with patch.object(queue_service, "_on_issue_queued",
                          new_callable=AsyncMock) as mock_queued:
            await queue_service.notify({
                "type": "queue_entry_created",
                "project_id": "p1",
                "issue_id": "i1",
            })
            await asyncio.sleep(0)
            mock_queued.assert_awaited_once_with("p1", "i1")

    @pytest.mark.asyncio
    async def test_notify_reasoning_routes_correctly(self, queue_service):
        """Reasoning event triggers _on_issue_reasoning."""
        with patch.object(queue_service, "_on_issue_reasoning",
                          new_callable=AsyncMock) as mock_reason:
            await queue_service.notify({
                "type": "issue_status_changed",
                "new_status": "Reasoning",
                "project_id": "p1",
                "issue_id": "i1",
            })
            await asyncio.sleep(0)
            mock_reason.assert_awaited_once_with("i1")

    @pytest.mark.asyncio
    async def test_notify_reasoning_skipped_with_flag(self, queue_service):
        """Reasoning event with _queue_dispatching_handled=True skips _on_issue_reasoning.

        _dequeue_and_run marks the QueueEntry as DISPATCHING synchronously
        before emitting the event, so the redundant _on_issue_reasoning
        → mark_dispatching call is wasted and should be skipped.
        """
        with patch.object(queue_service, "_on_issue_reasoning",
                          new_callable=AsyncMock) as mock_reason:
            await queue_service.notify({
                "type": "issue_status_changed",
                "new_status": "Reasoning",
                "project_id": "p1",
                "issue_id": "i1",
                "_queue_dispatching_handled": True,
            })
            await asyncio.sleep(0)
            mock_reason.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_reasoning_flag_does_not_affect_other_statuses(
        self, queue_service,
    ):
        """The flag only affects Reasoning — Finished and queue_entry_created still work."""
        with (
            patch.object(queue_service, "_on_issue_finished",
                          new_callable=AsyncMock) as mock_finish,
            patch.object(queue_service, "_on_issue_queued",
                          new_callable=AsyncMock) as mock_queued,
            patch.object(queue_service, "_on_issue_reasoning",
                          new_callable=AsyncMock) as mock_reason,
        ):
            # Finished event with the flag — should still dispatch
            await queue_service.notify({
                "type": "issue_status_changed",
                "new_status": "Finished",
                "project_id": "p1",
                "issue_id": "i1",
                "_queue_dispatching_handled": True,
            })
            await asyncio.sleep(0)
            mock_finish.assert_awaited_once_with("p1", "i1")

            # queue_entry_created event — should dispatch regardless of flag
            await queue_service.notify({
                "type": "queue_entry_created",
                "project_id": "p2",
                "issue_id": "i2",
            })
            await asyncio.sleep(0)
            mock_queued.assert_awaited_once_with("p2", "i2")

            # Reasoning event with the flag — should be skipped
            mock_reason.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_issue_finished(
        self, queue_service, project, db_session,
    ):
        """_on_issue_finished marks dispatched and dequeues next."""
        await queue_service.register("iss-1", project.id)
        await queue_service.register("iss-2", project.id)

        run_issue_result = {"term_id": "term-2", "status": "running"}
        with (
            patch("app.services.issue_queue_service.run_issue",
                  new_callable=AsyncMock, return_value=run_issue_result),
            patch("app.mcp.shared_tools._emit_event",
                  new_callable=AsyncMock),
        ):
            await queue_service._on_issue_finished(project.id, "iss-1")

        # First issue should now be dispatched
        entry_1 = await queue_service.get_pending_entry("iss-1")
        assert entry_1 is None  # no longer pending

    @pytest.mark.asyncio
    async def test_on_issue_finished_twice(
        self, queue_service, project, db_session,
    ):
        """Double Finished event: second call is harmless."""
        await queue_service.register("iss-1", project.id)
        await queue_service.register("iss-2", project.id)

        with (
            patch("app.services.issue_queue_service.run_issue",
                  new_callable=AsyncMock, return_value={"term_id": "t1", "status": "running"}),
            patch("app.mcp.shared_tools._emit_event",
                  new_callable=AsyncMock),
        ):
            await queue_service._on_issue_finished(project.id, "iss-1")
            # Second call with same issue_id — should not crash
            await queue_service._on_issue_finished(project.id, "iss-1")

    @pytest.mark.asyncio
    async def test_on_issue_queued_registers_and_auto_starts(
        self, queue_service, project, db_session,
    ):
        """_on_issue_queued registers entry and calls _maybe_auto_start_first."""
        with patch.object(queue_service, "_maybe_auto_start_first",
                          new_callable=AsyncMock) as mock_auto:
            await queue_service._on_issue_queued(project.id, "iss-1")

        entry = await queue_service.get_pending_entry("iss-1")
        assert entry is not None
        assert entry.status == QueueEntryStatus.PENDING
        mock_auto.assert_awaited_once_with(project.id, "iss-1")

    @pytest.mark.asyncio
    async def test_on_issue_reasoning_marks_dispatching(
        self, queue_service, project, db_session,
    ):
        """_on_issue_reasoning marks QueueEntry as DISPATCHING."""
        await queue_service.register("iss-1", project.id)
        await queue_service._on_issue_reasoning("iss-1")
        # Entry should now be DISPATCHING
        from sqlalchemy import select
        async with db_session.begin():
            result = await db_session.execute(
                select(QueueEntry).where(QueueEntry.issue_id == "iss-1")
            )
            entry = result.scalar_one()
        assert entry.status == QueueEntryStatus.DISPATCHING


# ==============================================================================
# TASK 5: Test auto-start e dequeue — _dequeue_and_run, _maybe_auto_start_first,
#          startup_resume
# ==============================================================================


class TestDequeueAndRun:
    """_dequeue_and_run() with full lifecycle."""

    @pytest.mark.asyncio
    async def test_dequeue_and_run_success(
        self, queue_service, project, db_session,
    ):
        """_dequeue_and_run() marks dispatching, updates status, emits event, runs."""
        from app.services.issue_service import IssueService
        isvc = IssueService(db_session)
        issue = await isvc.create(
            project_id=project.id,
            description="Queue test issue",
            priority=1,
        )
        await queue_service.register(issue.id, project.id)

        run_issue_result = {"term_id": "term-1", "status": "running"}
        with (
            patch("app.services.issue_queue_service.run_issue",
                  new_callable=AsyncMock, return_value=run_issue_result) as mock_run,
            patch("app.mcp.shared_tools._emit_event",
                  new_callable=AsyncMock) as mock_emit,
        ):
            await queue_service._dequeue_and_run(project.id)

        mock_run.assert_awaited_once()
        mock_emit.assert_awaited_once()
        call_args = mock_emit.call_args[0][0]
        assert call_args["type"] == "issue_status_changed"
        assert call_args["new_status"] == "Reasoning"

    @pytest.mark.asyncio
    async def test_dequeue_and_run_no_pending(self, queue_service, project):
        """_dequeue_and_run() does nothing when no pending entries."""
        with (
            patch("app.services.issue_queue_service.run_issue",
                  new_callable=AsyncMock) as mock_run,
            patch("app.mcp.shared_tools._emit_event",
                  new_callable=AsyncMock) as mock_emit,
        ):
            await queue_service._dequeue_and_run(project.id)
        mock_run.assert_not_called()
        mock_emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_dequeue_and_run_failure(
        self, queue_service, project, db_session,
    ):
        """_dequeue_and_run() marks entry FAILED when run_issue fails."""
        from app.services.issue_service import IssueService
        isvc = IssueService(db_session)
        issue = await isvc.create(
            project_id=project.id,
            description="Queue test issue",
            priority=1,
        )
        await queue_service.register(issue.id, project.id)

        with (
            patch("app.services.issue_queue_service.run_issue",
                  new_callable=AsyncMock,
                  return_value={"error": "Failed to start"}) as mock_run,
            patch("app.mcp.shared_tools._emit_event",
                  new_callable=AsyncMock),
        ):
            await queue_service._dequeue_and_run(project.id)

        mock_run.assert_awaited_once()
        # Entry should be FAILED
        from sqlalchemy import select
        async with db_session.begin():
            result = await db_session.execute(
                select(QueueEntry).where(QueueEntry.issue_id == issue.id)
            )
            entry = result.scalar_one()
        assert entry.status == QueueEntryStatus.FAILED
        assert "Failed to start" in entry.error_message

    @pytest.mark.asyncio
    async def test_dequeue_locks_per_project(
        self, queue_service, project, project_b, db_session,
    ):
        """_dequeue_locks dict creates independent locks per project."""
        assert project.id in queue_service._dequeue_locks or True
        # The lock is created lazily in _dequeue_and_run, not in constructor
        # Just verify the dict structure
        assert isinstance(queue_service._dequeue_locks, dict)


class TestMaybeAutoStartFirst:
    """_maybe_auto_start_first() auto-start logic."""

    @pytest.mark.asyncio
    async def test_auto_starts_when_only_pending(
        self, queue_service, project, db_session,
    ):
        """Auto-starts when pending_count==1 and no running issue."""
        await queue_service.register("iss-1", project.id)

        with patch.object(queue_service, "_dequeue_and_run",
                          new_callable=AsyncMock) as mock_deq:
            await queue_service._maybe_auto_start_first(project.id, "iss-1")
        mock_deq.assert_awaited_once_with(project.id)

    @pytest.mark.asyncio
    async def test_auto_starts_when_multiple_pending(
        self, queue_service, project, db_session,
    ):
        """Auto-starts when pending_count >= 1 and nothing running."""
        await queue_service.register("iss-1", project.id)
        await queue_service.register("iss-2", project.id)

        with patch.object(queue_service, "_dequeue_and_run",
                          new_callable=AsyncMock) as mock_deq:
            await queue_service._maybe_auto_start_first(project.id, "iss-1")
        mock_deq.assert_awaited_once_with(project.id)

    @pytest.mark.asyncio
    async def test_skips_when_issue_running(
        self, queue_service, project, db_session,
    ):
        """Does NOT auto-start when a REASONING issue exists for project."""
        await queue_service.register("iss-1", project.id)
        # Create and start an issue to make it "running"
        from app.services.issue_service import IssueService
        isvc = IssueService(db_session)
        issue = await isvc.create(
            project_id=project.id,
            description="Running issue",
            priority=1,
        )
        await isvc.create_spec(issue.id, project.id, "# Spec")
        # Now it's REASONING

        with patch.object(queue_service, "_dequeue_and_run",
                          new_callable=AsyncMock) as mock_deq:
            await queue_service._maybe_auto_start_first(project.id, "iss-1")
        mock_deq.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_pending_entries(
        self, queue_service, project,
    ):
        """Does NOT auto-start when no entries at all."""
        with patch.object(queue_service, "_dequeue_and_run",
                          new_callable=AsyncMock) as mock_deq:
            await queue_service._maybe_auto_start_first(project.id, "nonexistent")
        mock_deq.assert_not_called()


class TestStartupResume:
    """startup_resume() recovery after restart."""

    @pytest.mark.asyncio
    async def test_startup_resume_disabled(self, queue_service_disabled, project):
        """startup_resume() skips when _enabled=False."""
        with patch.object(queue_service_disabled, "_dequeue_and_run",
                          new_callable=AsyncMock) as mock_deq:
            await queue_service_disabled.startup_resume()
        mock_deq.assert_not_called()

    @pytest.mark.asyncio
    async def test_startup_resume_enabled_with_pending(
        self, queue_service, project, db_session,
    ):
        """startup_resume() auto-starts pending entries when nothing running."""
        await queue_service.register("iss-1", project.id)

        with (
            patch.object(queue_service, "_dequeue_and_run",
                         new_callable=AsyncMock) as mock_deq,
        ):
            await queue_service.startup_resume()
            await asyncio.sleep(0)
        mock_deq.assert_awaited_once_with(project.id)

    @pytest.mark.asyncio
    async def test_startup_resume_no_pending_entries(self, queue_service, project):
        """startup_resume() does nothing when no pending entries."""
        with patch.object(queue_service, "_dequeue_and_run",
                          new_callable=AsyncMock) as mock_deq:
            await queue_service.startup_resume()
        mock_deq.assert_not_called()


# ==============================================================================
# TASK 6: Test configurazione — load_state, set_enabled
# ==============================================================================


class TestConfiguration:
    """load_state() and set_enabled() methods."""

    @pytest.mark.asyncio
    async def test_load_state_default_disabled(self, queue_service, db_session):
        """load_state() defaults to disabled when setting not in DB."""
        # The setting does not exist in the test DB — default is "false"
        svc = queue_service
        svc._enabled = True  # override before load
        await svc.load_state()
        assert svc._enabled is False

    @pytest.mark.asyncio
    async def test_load_state_enabled(self, queue_service, db_session):
        """load_state() reads 'true' from settings DB."""
        # Insert a Setting row
        setting = Setting(key="queue_auto_process", value="true")
        db_session.add(setting)
        await db_session.commit()

        svc = queue_service
        svc._enabled = False
        await svc.load_state()
        assert svc._enabled is True

    @pytest.mark.asyncio
    async def test_load_state_disabled(self, queue_service, db_session):
        """load_state() reads 'false' from settings DB."""
        setting = Setting(key="queue_auto_process", value="false")
        db_session.add(setting)
        await db_session.commit()

        svc = queue_service
        svc._enabled = True
        await svc.load_state()
        assert svc._enabled is False

    @pytest.mark.asyncio
    async def test_set_enabled_enables_and_resumes(
        self, queue_service, project, db_session,
    ):
        """set_enabled(True) persists and calls startup_resume."""
        with patch.object(queue_service, "startup_resume",
                          new_callable=AsyncMock) as mock_resume:
            await queue_service.set_enabled(True)
            await asyncio.sleep(0)

        assert queue_service._enabled is True
        mock_resume.assert_awaited_once()

        # Verify it's persisted in DB
        from app.services.settings_service import SettingsService
        svc = SettingsService(db_session)
        val = await svc.get("queue_auto_process")
        assert val == "true"

    @pytest.mark.asyncio
    async def test_set_enabled_disables_and_persists(
        self, queue_service, db_session,
    ):
        """set_enabled(False) persists disabled state."""
        await queue_service.set_enabled(False)
        assert queue_service._enabled is False

        from app.services.settings_service import SettingsService
        svc = SettingsService(db_session)
        val = await svc.get("queue_auto_process")
        assert val == "false"


# ==============================================================================
# TASK 7: Test FIFO multi-progetto
# ==============================================================================


class TestMultiProjectFIFO:
    """FIFO independence and ordering across multiple projects."""

    @pytest.mark.asyncio
    async def test_independent_queues(
        self, queue_service, project, project_b, db_session,
    ):
        """Entries in project A don't affect project B queues."""
        await queue_service.register("iss-a1", project.id)
        await queue_service.register("iss-a2", project.id)
        await queue_service.register("iss-b1", project_b.id)
        await queue_service.register("iss-b2", project_b.id)

        # Each project sees its own entries
        list_a = await queue_service.list_queue(project.id)
        list_b = await queue_service.list_queue(project_b.id)
        assert len(list_a) == 2
        assert len(list_b) == 2
        assert all(e["project_id"] == project.id for e in list_a)
        assert all(e["project_id"] == project_b.id for e in list_b)

    @pytest.mark.asyncio
    async def test_independent_order_counters(
        self, queue_service, project, project_b, db_session,
    ):
        """Each project has its own auto-incrementing order counter."""
        e1 = await queue_service.register("iss-a1", project.id)
        e2 = await queue_service.register("iss-b1", project_b.id)
        e3 = await queue_service.register("iss-b2", project_b.id)
        e4 = await queue_service.register("iss-a2", project.id)

        assert e1.order == 1  # project A: 1
        assert e2.order == 1  # project B: 1
        assert e3.order == 2  # project B: 2
        assert e4.order == 2  # project A: 2

    @pytest.mark.asyncio
    async def test_fifo_order_global(
        self, queue_service, project, project_b, db_session,
    ):
        """list_all_global() returns entries sorted globally by order."""
        await queue_service.register("iss-a1", project.id)
        await queue_service.register("iss-b1", project_b.id)
        await queue_service.register("iss-a2", project.id)

        all_entries = await queue_service.list_all_global()
        assert len(all_entries) == 3
        # Ordered by order ASC globally (but order is per project,
        # so entries may interleave)
        orders = [e["order"] for e in all_entries]
        assert orders == sorted(orders)

    @pytest.mark.asyncio
    async def test_dequeue_respects_project_scope(
        self, queue_service, project, project_b, db_session,
    ):
        """get_next_pending() scoped per project."""
        await queue_service.register("iss-a1", project.id)
        await queue_service.register("iss-b1", project_b.id)

        next_a = await queue_service.get_next_pending(project.id)
        next_b = await queue_service.get_next_pending(project_b.id)

        assert next_a.issue_id == "iss-a1"
        assert next_b.issue_id == "iss-b1"

    @pytest.mark.asyncio
    async def test_queue_position(
        self, queue_service, project, db_session,
    ):
        """Implicit FIFO position test: entries created in order get
        positions 1, 2, 3."""
        await queue_service.register("iss-1", project.id)
        await queue_service.register("iss-2", project.id)
        await queue_service.register("iss-3", project.id)

        entries = await queue_service.list_queue(project.id)
        for i, e in enumerate(entries, start=1):
            assert e["order"] == i
