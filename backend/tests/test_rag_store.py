import tempfile

from app.rag.store import VectorStore


def _make_store(tmp_dir, dimension=4):
    return VectorStore(db_path=tmp_dir, dimension=dimension)


def test_add_and_search():
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.add([
            {
                "id": "chunk-1",
                "project_id": "proj-1",
                "chunk_text": "authentication with OAuth",
                "vector": [1.0, 0.0, 0.0, 0.0],
                "source_type": "file",
                "source_id": "file-1",
                "title": "auth.txt",
                "chunk_index": 0,
                "total_chunks": 1,
                "metadata": "{}",
                "created_at": "2026-01-01T00:00:00",
            }
        ])
        results = store.search([1.0, 0.0, 0.0, 0.0], project_id="proj-1", limit=5)
        assert len(results) == 1
        assert results[0]["chunk_id"] == "chunk-1"
        assert "score" in results[0]


def test_search_filters_by_project():
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.add([
            {
                "id": "c1", "project_id": "proj-1", "chunk_text": "hello",
                "vector": [1.0, 0.0, 0.0, 0.0], "source_type": "file",
                "source_id": "f1", "title": "a.txt", "chunk_index": 0,
                "total_chunks": 1, "metadata": "{}", "created_at": "2026-01-01T00:00:00",
            },
            {
                "id": "c2", "project_id": "proj-2", "chunk_text": "world",
                "vector": [0.0, 1.0, 0.0, 0.0], "source_type": "file",
                "source_id": "f2", "title": "b.txt", "chunk_index": 0,
                "total_chunks": 1, "metadata": "{}", "created_at": "2026-01-01T00:00:00",
            },
        ])
        results = store.search([1.0, 0.0, 0.0, 0.0], project_id="proj-1", limit=5)
        assert all(r["project_id"] == "proj-1" for r in results)


def test_search_filters_by_source_type():
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.add([
            {
                "id": "c1", "project_id": "p1", "chunk_text": "file content",
                "vector": [1.0, 0.0, 0.0, 0.0], "source_type": "file",
                "source_id": "f1", "title": "a.txt", "chunk_index": 0,
                "total_chunks": 1, "metadata": "{}", "created_at": "2026-01-01T00:00:00",
            },
            {
                "id": "c2", "project_id": "p1", "chunk_text": "issue content",
                "vector": [0.9, 0.1, 0.0, 0.0], "source_type": "issue",
                "source_id": "i1", "title": "Issue #1", "chunk_index": 0,
                "total_chunks": 1, "metadata": "{}", "created_at": "2026-01-01T00:00:00",
            },
        ])
        results = store.search(
            [1.0, 0.0, 0.0, 0.0], project_id="p1", source_type="issue", limit=5
        )
        assert all(r["source_type"] == "issue" for r in results)


def test_delete_by_source():
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.add([
            {
                "id": "c1", "project_id": "p1", "chunk_text": "text",
                "vector": [1.0, 0.0, 0.0, 0.0], "source_type": "file",
                "source_id": "file-1", "title": "a.txt", "chunk_index": 0,
                "total_chunks": 1, "metadata": "{}", "created_at": "2026-01-01T00:00:00",
            },
        ])
        store.delete_by_source("file-1")
        results = store.search([1.0, 0.0, 0.0, 0.0], project_id="p1", limit=5)
        assert len(results) == 0


def test_get_chunk():
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.add([
            {
                "id": "c1", "project_id": "p1", "chunk_text": "full text here",
                "vector": [1.0, 0.0, 0.0, 0.0], "source_type": "file",
                "source_id": "f1", "title": "a.txt", "chunk_index": 0,
                "total_chunks": 3, "metadata": '{"mime_type": "text/plain"}',
                "created_at": "2026-01-01T00:00:00",
            },
            {
                "id": "c2", "project_id": "p1", "chunk_text": "second chunk",
                "vector": [0.0, 1.0, 0.0, 0.0], "source_type": "file",
                "source_id": "f1", "title": "a.txt", "chunk_index": 1,
                "total_chunks": 3, "metadata": '{"mime_type": "text/plain"}',
                "created_at": "2026-01-01T00:00:00",
            },
        ])
        chunk = store.get_chunk("c1", project_id="p1")
        assert chunk is not None
        assert chunk["chunk_text"] == "full text here"
        assert chunk["total_chunks"] == 3
        assert chunk["adjacent_chunks"]["previous"] is None
        assert chunk["adjacent_chunks"]["next"] == "c2"


def test_get_chunk_wrong_project_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.add([
            {
                "id": "c1", "project_id": "p1", "chunk_text": "text",
                "vector": [1.0, 0.0, 0.0, 0.0], "source_type": "file",
                "source_id": "f1", "title": "a.txt", "chunk_index": 0,
                "total_chunks": 1, "metadata": "{}", "created_at": "2026-01-01T00:00:00",
            },
        ])
        result = store.get_chunk("c1", project_id="wrong-project")
        assert result is None
