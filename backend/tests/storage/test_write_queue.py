import pytest

from app.storage.write_queue import WriteQueue


@pytest.fixture
def queue(tmp_path):
    db_path = str(tmp_path / "test_queue.db")
    q = WriteQueue(db_path)
    yield q
    q.close()


class TestEnqueue:
    def test_enqueue_adds_row(self, queue):
        queue.enqueue("/p", "memories", "r1", "upsert", {"key": "val"}, "2026-01-01T00:00:00")
        batch = queue.dequeue_batch()
        assert len(batch) == 1
        assert batch[0]["record_id"] == "r1"
        assert batch[0]["action"] == "upsert"

    def test_enqueue_deduplicates_by_record(self, queue):
        queue.enqueue("/p", "memories", "r1", "upsert", {"v": 1}, "2026-01-01T00:00:00")
        queue.enqueue("/p", "memories", "r1", "upsert", {"v": 2}, "2026-01-02T00:00:00")
        batch = queue.dequeue_batch()
        assert len(batch) == 1
        payload = batch[0]["payload_json"]
        assert '"v": 2' in payload

    def test_enqueue_different_records_keep_both(self, queue):
        queue.enqueue("/p", "memories", "r1", "upsert", {}, "2026-01-01T00:00:00")
        queue.enqueue("/p", "memories", "r2", "upsert", {}, "2026-01-01T00:00:00")
        assert queue.count_pending() == 2

    def test_enqueue_different_stores_keep_both(self, queue):
        queue.enqueue("/p", "memories", "r1", "upsert", {}, "2026-01-01T00:00:00")
        queue.enqueue("/p", "issues", "r1", "upsert", {}, "2026-01-01T00:00:00")
        assert queue.count_pending() == 2

    def test_enqueue_delete_with_null_payload(self, queue):
        queue.enqueue("/p", "memories", "r1", "delete", None, "2026-01-01T00:00:00")
        batch = queue.dequeue_batch()
        assert batch[0]["action"] == "delete"
        assert batch[0]["payload_json"] is None


class TestDequeueBatch:
    def test_dequeue_respects_limit(self, queue):
        for i in range(25):
            queue.enqueue("/p", "memories", f"r{i}", "upsert", {}, "2026-01-01T00:00:00")
        batch = queue.dequeue_batch(limit=10)
        assert len(batch) == 10

    def test_dequeue_empty_returns_empty(self, queue):
        assert queue.dequeue_batch() == []

    def test_dequeue_returns_in_order(self, queue):
        queue.enqueue("/p", "memories", "r1", "upsert", {}, "2026-01-01T00:00:00")
        queue.enqueue("/p", "memories", "r2", "upsert", {}, "2026-01-01T00:00:00")
        batch = queue.dequeue_batch()
        assert batch[0]["record_id"] == "r1"
        assert batch[1]["record_id"] == "r2"


class TestRemove:
    def test_remove_deletes_row(self, queue):
        queue.enqueue("/p", "memories", "r1", "upsert", {}, "2026-01-01T00:00:00")
        batch = queue.dequeue_batch()
        queue.remove(batch[0]["id"])
        assert queue.count_pending() == 0


class TestRetry:
    def test_increment_retry_counts_up(self, queue):
        queue.enqueue("/p", "memories", "r1", "upsert", {}, "2026-01-01T00:00:00")
        batch = queue.dequeue_batch()
        row_id = batch[0]["id"]
        assert queue.increment_retry(row_id) == 1
        assert queue.increment_retry(row_id) == 2
        assert queue.increment_retry(row_id) == 3


class TestCountPending:
    def test_count_returns_correct(self, queue):
        assert queue.count_pending() == 0
        queue.enqueue("/p", "memories", "r1", "upsert", {}, "2026-01-01T00:00:00")
        assert queue.count_pending() == 1
