from unittest.mock import MagicMock, AsyncMock

import pytest


@pytest.fixture
def mock_pipeline():
    pipeline = MagicMock()
    pipeline.embed_file.return_value = "ok"
    pipeline.embed_issue.return_value = "ok"
    pipeline.store = MagicMock()
    pipeline.store.search.return_value = [{"chunk_id": "c1", "score": 0.9}]
    pipeline.store.get_chunk.return_value = {"chunk_id": "c1", "chunk_text": "hello"}
    pipeline.driver = MagicMock()
    pipeline.driver.embed.return_value = [[0.1, 0.2, 0.3, 0.4]]
    return pipeline


@pytest.fixture
def mock_event_service():
    svc = MagicMock()
    svc.emit = AsyncMock()
    return svc


async def test_embed_file_async(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/test.txt", mime_type="text/plain",
        original_name="test.txt", project_name="My Project",
    )
    mock_pipeline.embed_file.assert_called_once()
    mock_event_service.emit.assert_called_once()
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_completed"
    assert event["project_name"] == "My Project"
    assert event["project_id"] == "p1"


async def test_embed_file_skipped(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    mock_pipeline.embed_file.return_value = "skipped"
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/test.docx", mime_type="application/msword",
        original_name="test.docx", project_name="My Project",
    )
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_skipped"
    assert event["project_name"] == "My Project"
    assert event["project_id"] == "p1"


async def test_embed_issue_async(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_issue(
        project_id="p1", source_id="i1",
        issue_data={"name": "Test", "specification": "spec"},
        project_name="My Project",
    )
    mock_pipeline.embed_issue.assert_called_once()
    event = mock_event_service.emit.call_args[0][0]
    assert event["project_name"] == "My Project"
    assert event["project_id"] == "p1"


async def test_search(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    results = await svc.search(query="test", project_id="p1", limit=5)
    assert len(results) == 1
    mock_pipeline.driver.embed.assert_called_once_with(["test"])


async def test_get_chunk_details(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    result = await svc.get_chunk_details(chunk_id="c1", project_id="p1")
    assert result["chunk_id"] == "c1"


async def test_delete_source(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.delete_source("f1")
    mock_pipeline.delete_source.assert_called_once_with("f1")


async def test_embed_file_failure_broadcasts_event(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    mock_pipeline.embed_file.side_effect = RuntimeError("extraction failed")
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/test.txt", mime_type="text/plain",
        original_name="test.txt", project_name="My Project",
    )
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_failed"
    assert "extraction failed" in event["error"]
    assert event["project_name"] == "My Project"
    assert event["project_id"] == "p1"


async def test_embed_file_retries_once_on_failure(mock_pipeline, mock_event_service, monkeypatch):
    """First call fails → retry → second call succeeds → emit completed."""
    from app.services.rag_service import RagService

    monkeypatch.setattr("app.services.rag_service.RETRY_BACKOFF_SECONDS", 0)

    calls = {"n": 0}

    def flaky(*a, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return "ok"

    mock_pipeline.embed_file.side_effect = flaky
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/t.txt", mime_type="text/plain",
        original_name="t.txt",
    )
    assert calls["n"] == 2
    # Last emit must be "completed", not "failed"
    final_event = mock_event_service.emit.call_args[0][0]
    assert final_event["type"] == "embedding_completed"


async def test_embed_file_marks_failed_after_retries(mock_pipeline, mock_event_service, monkeypatch):
    from app.services.rag_service import RagService

    monkeypatch.setattr("app.services.rag_service.RETRY_BACKOFF_SECONDS", 0)
    mock_pipeline.embed_file.side_effect = RuntimeError("always fails")
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/t.txt", mime_type="text/plain",
        original_name="t.txt",
    )
    assert mock_pipeline.embed_file.call_count == 2
    final_event = mock_event_service.emit.call_args[0][0]
    assert final_event["type"] == "embedding_failed"
    assert "always fails" in final_event["error"]


async def test_embed_issue_retries_once_on_failure(mock_pipeline, mock_event_service, monkeypatch):
    from app.services.rag_service import RagService

    monkeypatch.setattr("app.services.rag_service.RETRY_BACKOFF_SECONDS", 0)

    calls = {"n": 0}

    def flaky(*a, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return "ok"

    mock_pipeline.embed_issue.side_effect = flaky
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_issue(
        project_id="p1", source_id="i1",
        issue_data={"name": "T"},
    )
    assert calls["n"] == 2
    final_event = mock_event_service.emit.call_args[0][0]
    assert final_event["type"] == "embedding_completed"


async def test_source_lock_serializes_concurrent_calls():
    """N coroutine concorrenti sullo stesso source_id vengono serializzate e il lock viene pulito."""
    import asyncio
    from app.services.rag_service import _source_lock, _source_locks

    _source_locks.clear()

    active_count = 0
    max_concurrent = 0

    async def worker():
        nonlocal active_count, max_concurrent
        async with _source_lock("source-concurrent"):
            active_count += 1
            max_concurrent = max(max_concurrent, active_count)
            await asyncio.sleep(0)  # cede il controllo per permettere interleaving
            active_count -= 1

    await asyncio.gather(*[worker() for _ in range(6)])

    assert max_concurrent == 1, "Al massimo una coroutine alla volta deve essere dentro il lock"
    assert "source-concurrent" not in _source_locks, "Il lock deve essere rimosso dopo l'ultimo uso"
