import asyncio

import pytest

from app.storage.background_writer import BackgroundWriter
from app.storage.write_queue import WriteQueue


@pytest.fixture
def queue_and_writer(tmp_path):
    db_path = str(tmp_path / "test_writer_queue.db")
    q = WriteQueue(db_path)
    writer = BackgroundWriter(q)
    yield q, writer


class TestBackgroundWriterLifecycle:
    @pytest.mark.asyncio
    async def test_start_and_stop(self, queue_and_writer):
        q, writer = queue_and_writer
        await writer.start()
        assert writer._running
        await writer.stop()
        assert not writer._running

    @pytest.mark.asyncio
    async def test_ensure_running_starts_writer(self, queue_and_writer):
        q, writer = queue_and_writer
        writer.ensure_running()
        await asyncio.sleep(0.1)
        assert writer._running
        await writer.stop()

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self, queue_and_writer):
        q, writer = queue_and_writer
        await writer.start()
        await writer.start()
        await writer.stop()

    @pytest.mark.asyncio
    async def test_flush_remaining_on_stop(self, queue_and_writer):
        q, writer = queue_and_writer
        q.enqueue("/p", "memories", "flush1", "delete", None, "2026-01-01T00:00:00")
        await writer.start()
        await asyncio.sleep(0.1)
        await writer.stop()
        assert q.count_pending() == 0

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self, queue_and_writer):
        q, writer = queue_and_writer
        await writer.stop()
