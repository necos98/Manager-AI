import tempfile
from unittest.mock import MagicMock

from app.rag.pipeline import EmbeddingPipeline
from app.rag.extractors.base import ExtractedContent, ExtractorRegistry
from app.rag.extractors.txt_extractor import TxtExtractor
from app.rag.chunker import TextChunker


def _mock_driver(dimension=4):
    driver = MagicMock()
    driver.dimension = dimension
    driver.embed.side_effect = lambda texts: [[0.1, 0.2, 0.3, 0.4]] * len(texts)
    return driver


def _mock_store():
    store = MagicMock()
    return store


def test_pipeline_embed_file():
    registry = ExtractorRegistry()
    registry.register(TxtExtractor())
    driver = _mock_driver()
    store = _mock_store()
    chunker = TextChunker(max_tokens=500, overlap_tokens=50)
    pipeline = EmbeddingPipeline(registry=registry, chunker=chunker, driver=driver, store=store)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Test content for embedding.")
        f.flush()
        pipeline.embed_file(
            project_id="proj-1",
            source_id="file-1",
            file_path=f.name,
            mime_type="text/plain",
            original_name="test.txt",
        )

    import os
    os.unlink(f.name)

    driver.embed.assert_called_once()
    store.delete_by_source.assert_called_once_with("file-1")
    store.add.assert_called_once()
    records = store.add.call_args[0][0]
    assert len(records) >= 1
    assert records[0]["project_id"] == "proj-1"
    assert records[0]["source_type"] == "file"
    assert records[0]["source_id"] == "file-1"


def test_pipeline_embed_issue():
    registry = ExtractorRegistry()
    driver = _mock_driver()
    store = _mock_store()
    chunker = TextChunker(max_tokens=500, overlap_tokens=50)
    pipeline = EmbeddingPipeline(registry=registry, chunker=chunker, driver=driver, store=store)

    issue_data = {
        "name": "Test Issue",
        "specification": "The spec content.",
        "plan": "The plan content.",
        "recap": "The recap content.",
    }
    pipeline.embed_issue(project_id="proj-1", source_id="issue-1", issue_data=issue_data)

    driver.embed.assert_called_once()
    store.delete_by_source.assert_called_once_with("issue-1")
    store.add.assert_called_once()
    records = store.add.call_args[0][0]
    assert records[0]["source_type"] == "issue"


def test_pipeline_unsupported_mimetype():
    registry = ExtractorRegistry()
    driver = _mock_driver()
    store = _mock_store()
    chunker = TextChunker()
    pipeline = EmbeddingPipeline(registry=registry, chunker=chunker, driver=driver, store=store)

    result = pipeline.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/path.docx", mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        original_name="doc.docx",
    )
    assert result == "skipped"
    store.add.assert_not_called()


def test_pipeline_delete_source():
    store = _mock_store()
    pipeline = EmbeddingPipeline(
        registry=ExtractorRegistry(), chunker=TextChunker(),
        driver=_mock_driver(), store=store,
    )
    pipeline.delete_source("file-1")
    store.delete_by_source.assert_called_once_with("file-1")
