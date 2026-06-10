"""Debug test for issue_queue_service_ref in test context."""
import asyncio
from unittest.mock import patch
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio

from app.models.queue_entry import QueueEntry, QueueEntryStatus
from app.services import event_service as evt_mod
from app.services.issue_queue_service import IssueQueueService, issue_queue_service_ref


@asynccontextmanager
async def _fake_session(db_session):
    yield db_session


@pytest.mark.asyncio
async def test_ref_is_set_after_init(db_session):
    """Debug: verify issue_queue_service_ref is set after creating IssueQueueService."""
    patcher = patch(
        "app.services.issue_queue_service.async_session",
        lambda: _fake_session(db_session),
        create=True,
    )
    patcher.start()
    try:
        print(f"  Before: issue_queue_service_ref = {issue_queue_service_ref!r}")
        svc = IssueQueueService()
        print(f"  After:  issue_queue_service_ref = {issue_queue_service_ref!r}")
        print(f"  svc = {svc!r}")
        print(f"  same? {issue_queue_service_ref is svc}")
        print(f"  in notifiers? {svc in evt_mod.event_service._notifiers}")
        assert issue_queue_service_ref is not None
        assert svc in evt_mod.event_service._notifiers
    finally:
        patcher.stop()


@pytest.mark.asyncio
async def test_plain_constructor(db_session):
    """Without patching async_session."""
    print(f"  Before plain: ref = {issue_queue_service_ref!r}")
    svc = IssueQueueService()
    print(f"  After plain:  ref = {issue_queue_service_ref!r}")
    print(f"  notifiers now: {len(evt_mod.event_service._notifiers)}")
    assert svc in evt_mod.event_service._notifiers
    assert issue_queue_service_ref is not None
