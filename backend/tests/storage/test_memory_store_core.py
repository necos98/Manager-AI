import pytest

from app.storage.memory_store_core import MemoryStore


@pytest.fixture
def store():
    s = MemoryStore()
    yield s
    s.reset()


class TestInitProject:
    def test_init_creates_project_entry(self, store):
        store.init_project("/p", "memories", {"a": "rec_a"}, [{"id": "a"}])
        assert store.has_project("/p")

    def test_init_multiple_store_types(self, store):
        store.init_project("/p", "memories", {"a": "rec_a"}, [{"id": "a"}])
        store.init_project("/p", "issues", {"b": "rec_b"}, [{"id": "b"}])
        assert store.get("/p", "memories", "a") == "rec_a"
        assert store.get("/p", "issues", "b") == "rec_b"

    def test_init_overwrites_existing(self, store):
        store.init_project("/p", "memories", {"a": "old"}, [{"id": "a"}])
        store.init_project("/p", "memories", {"a": "new"}, [{"id": "a", "created_at": "2026-01-01"}])
        assert store.get("/p", "memories", "a") == "new"

    def test_multiple_projects_isolated(self, store):
        store.init_project("/p1", "memories", {"a": "rec_a"}, [{"id": "a"}])
        store.init_project("/p2", "memories", {"b": "rec_b"}, [{"id": "b"}])
        assert store.get("/p1", "memories", "a") == "rec_a"
        assert store.get("/p2", "memories", "b") == "rec_b"
        assert store.get("/p1", "memories", "b") is None


class TestRemoveProject:
    def test_remove_clears_all_data(self, store):
        store.init_project("/p", "memories", {"a": "rec_a"}, [{"id": "a"}])
        store.remove_project("/p")
        assert not store.has_project("/p")
        assert store.get("/p", "memories", "a") is None

    def test_remove_nonexistent_is_noop(self, store):
        store.remove_project("/nonexistent")


class TestGet:
    def test_get_existing(self, store):
        store.init_project("/p", "memories", {"a": "hello"}, [{"id": "a"}])
        assert store.get("/p", "memories", "a") == "hello"

    def test_get_missing_record(self, store):
        store.init_project("/p", "memories", {"a": "hello"}, [{"id": "a"}])
        assert store.get("/p", "memories", "b") is None

    def test_get_missing_project(self, store):
        assert store.get("/nonexistent", "memories", "a") is None

    def test_get_missing_store_type(self, store):
        store.init_project("/p", "memories", {}, [])
        assert store.get("/p", "files", "a") is None


class TestListIndex:
    def test_list_returns_index(self, store):
        index = [
            {"id": "a", "created_at": "2026-01-01"},
            {"id": "b", "created_at": "2026-01-02"},
        ]
        store.init_project("/p", "memories", {"a": "r_a", "b": "r_b"}, index)
        result = store.list_index("/p", "memories")
        assert len(result) == 2
        assert result[0]["id"] == "a"

    def test_list_empty_project(self, store):
        store.init_project("/p", "memories", {}, [])
        assert store.list_index("/p", "memories") == []

    def test_list_missing_project(self, store):
        assert store.list_index("/nonexistent", "memories") == []


class TestListAll:
    def test_list_all_returns_records(self, store):
        store.init_project("/p", "memories", {"a": "r_a", "b": "r_b"}, [{"id": "a"}, {"id": "b"}])
        result = store.list_all("/p", "memories")
        assert len(result) == 2
        assert set(result) == {"r_a", "r_b"}


class TestUpsert:
    def test_upsert_new_record(self, store):
        store.upsert("/p", "memories", "a", "rec_a", {"id": "a", "created_at": "2026-01-01"})
        assert store.get("/p", "memories", "a") == "rec_a"
        idx = store.list_index("/p", "memories")
        assert idx[0]["id"] == "a"

    def test_upsert_updates_existing(self, store):
        store.upsert("/p", "memories", "a", "old", {"id": "a", "created_at": "2026-01-01"})
        store.upsert("/p", "memories", "a", "new", {"id": "a", "created_at": "2026-01-02"})
        assert store.get("/p", "memories", "a") == "new"

    def test_upsert_sorts_index_by_created_at(self, store):
        store.upsert("/p", "memories", "b", "r_b", {"id": "b", "created_at": "2026-01-02"})
        store.upsert("/p", "memories", "a", "r_a", {"id": "a", "created_at": "2026-01-01"})
        idx = store.list_index("/p", "memories")
        assert idx[0]["id"] == "a"
        assert idx[1]["id"] == "b"


class TestDelete:
    def test_delete_removes_record_and_index(self, store):
        store.init_project("/p", "memories", {"a": "r_a"}, [{"id": "a"}])
        store.delete("/p", "memories", "a")
        assert store.get("/p", "memories", "a") is None
        assert store.list_index("/p", "memories") == []

    def test_delete_nonexistent_is_noop(self, store):
        store.delete("/p", "memories", "nonexistent")


class TestReset:
    def test_reset_clears_all(self, store):
        store.init_project("/p1", "memories", {"a": "r_a"}, [{"id": "a"}])
        store.init_project("/p2", "issues", {"b": "r_b"}, [{"id": "b"}])
        store.reset()
        assert not store.has_project("/p1")
        assert not store.has_project("/p2")
