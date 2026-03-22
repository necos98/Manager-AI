# RAG System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable LLM semantic search over project files and completed issues via two new MCP tools, backed by LanceDB vector storage.

**Architecture:** A `rag/` package handles content extraction, chunking, and embedding with pluggable drivers. Files and issues are embedded asynchronously into a single LanceDB table. Two MCP tools (`search_project_context`, `get_context_chunk_details`) expose the search interface.

**Tech Stack:** Python, FastAPI, LanceDB, sentence-transformers (all-MiniLM-L6-v2), pypdf

**Spec:** `docs/superpowers/specs/2026-03-22-rag-system-design.md`

---

### Task 1: Add dependencies and config

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add new dependencies to requirements.txt**

Add to `backend/requirements.txt`:
```
sentence-transformers>=3.0.0
pypdf>=4.0.0
```

- [ ] **Step 2: Add RAG settings to config.py**

Add to `backend/app/config.py` in the `Settings` class:
```python
embedding_driver: str = "sentence_transformer"
embedding_model: str = "all-MiniLM-L6-v2"
chunk_max_tokens: int = 500
chunk_overlap_tokens: int = 50
```

- [ ] **Step 3: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt backend/app/config.py
git commit -m "feat(rag): add sentence-transformers, pypdf deps and config settings"
```

---

### Task 2: Embedding driver interface and SentenceTransformer driver

**Files:**
- Create: `backend/app/rag/__init__.py`
- Create: `backend/app/rag/drivers/__init__.py`
- Create: `backend/app/rag/drivers/base.py`
- Create: `backend/app/rag/drivers/sentence_transformer.py`
- Create: `backend/tests/test_rag_drivers.py`

- [ ] **Step 1: Create package structure**

Create `backend/app/rag/__init__.py` with the RAG service singleton (avoids circular imports — `main.py` sets it, `routers/files.py` and `mcp/server.py` import it from here):
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.rag_service import RagService

_rag_service: RagService | None = None


def get_rag_service() -> RagService:
    """Get the RAG service singleton. Initialized in app lifespan."""
    if _rag_service is None:
        raise RuntimeError("RAG service not initialized. App lifespan not started.")
    return _rag_service


def set_rag_service(service: RagService | None):
    """Set the RAG service singleton. Called from app lifespan."""
    global _rag_service
    _rag_service = service
```

Create empty `backend/app/rag/drivers/__init__.py`.

- [ ] **Step 2: Write the driver interface**

Create `backend/app/rag/drivers/base.py`:
```python
from abc import ABC, abstractmethod


class EmbeddingDriver(ABC):
    """Abstract interface for embedding drivers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension of the embedding vectors."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into vectors. Synchronous (CPU-bound)."""
```

- [ ] **Step 3: Write failing test for SentenceTransformerDriver**

Create `backend/tests/test_rag_drivers.py`:
```python
from unittest.mock import MagicMock, patch


def test_sentence_transformer_dimension():
    from app.rag.drivers.sentence_transformer import SentenceTransformerDriver
    with patch("app.rag.drivers.sentence_transformer.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_cls.return_value = mock_model
        driver = SentenceTransformerDriver(model_name="all-MiniLM-L6-v2")
        assert driver.dimension == 384


def test_sentence_transformer_embed():
    from app.rag.drivers.sentence_transformer import SentenceTransformerDriver
    with patch("app.rag.drivers.sentence_transformer.SentenceTransformer") as mock_cls:
        import numpy as np
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.random.rand(2, 384).astype(np.float32)
        mock_cls.return_value = mock_model
        driver = SentenceTransformerDriver(model_name="all-MiniLM-L6-v2")
        result = driver.embed(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == 384
        mock_model.encode.assert_called_once_with(["hello", "world"], batch_size=32)


def test_sentence_transformer_lazy_loading():
    from app.rag.drivers.sentence_transformer import SentenceTransformerDriver
    with patch("app.rag.drivers.sentence_transformer.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_cls.return_value = mock_model
        driver = SentenceTransformerDriver(model_name="all-MiniLM-L6-v2")
        # Constructor should NOT load the model yet
        mock_cls.assert_not_called()
        # Accessing dimension triggers loading
        _ = driver.dimension
        mock_cls.assert_called_once_with("all-MiniLM-L6-v2")
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_rag_drivers.py -v`
Expected: FAIL (module not found)

- [ ] **Step 5: Implement SentenceTransformerDriver**

Create `backend/app/rag/drivers/sentence_transformer.py`:
```python
from app.rag.drivers.base import EmbeddingDriver

BATCH_SIZE = 32


class SentenceTransformerDriver(EmbeddingDriver):
    """Embedding driver using sentence-transformers (local, CPU-based)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)

    @property
    def dimension(self) -> int:
        self._load_model()
        return self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load_model()
        embeddings = self._model.encode(texts, batch_size=BATCH_SIZE)
        return [vec.tolist() for vec in embeddings]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_rag_drivers.py -v`
Expected: 3 PASSED

- [ ] **Step 7: Commit**

```bash
git add backend/app/rag/ backend/tests/test_rag_drivers.py
git commit -m "feat(rag): add embedding driver interface and sentence-transformer implementation"
```

---

### Task 3: TextChunker

**Files:**
- Create: `backend/app/rag/chunker.py`
- Create: `backend/tests/test_rag_chunker.py`

- [ ] **Step 1: Write failing tests for TextChunker**

Create `backend/tests/test_rag_chunker.py`:
```python
from app.rag.chunker import TextChunker, Chunk


def test_chunk_dataclass():
    c = Chunk(text="hello", index=0)
    assert c.text == "hello"
    assert c.index == 0


def test_single_short_paragraph():
    chunker = TextChunker(max_tokens=500, overlap_tokens=50)
    result = chunker.chunk("This is a short paragraph.")
    assert len(result) == 1
    assert result[0].text == "This is a short paragraph."
    assert result[0].index == 0


def test_multiple_paragraphs_under_limit():
    chunker = TextChunker(max_tokens=500, overlap_tokens=50)
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = chunker.chunk(text)
    # Each paragraph is short, but merge-small should combine them
    # Total ~6 words, well under 500
    assert len(result) == 1


def test_merge_small_paragraphs():
    chunker = TextChunker(max_tokens=20, overlap_tokens=5)
    text = "One.\n\nTwo.\n\nThree."
    result = chunker.chunk(text)
    # All are tiny, should merge into one chunk (3 words total < 20)
    assert len(result) == 1
    assert "One." in result[0].text
    assert "Three." in result[0].text


def test_split_large_paragraph():
    chunker = TextChunker(max_tokens=10, overlap_tokens=2)
    # Create a paragraph with ~20 words (no \n\n so it's one paragraph)
    words = ["word"] * 20
    text = " ".join(words)
    result = chunker.chunk(text)
    assert len(result) >= 2
    # Each chunk should be roughly max_tokens or less
    for chunk in result:
        word_count = len(chunk.text.split())
        assert word_count <= 12  # max_tokens + some tolerance for overlap


def test_mixed_paragraphs():
    chunker = TextChunker(max_tokens=10, overlap_tokens=2)
    short = "Short."
    long = " ".join(["word"] * 20)
    text = f"{short}\n\n{long}"
    result = chunker.chunk(text)
    # Short paragraph + long paragraph that gets split
    assert len(result) >= 2


def test_empty_text():
    chunker = TextChunker(max_tokens=500, overlap_tokens=50)
    result = chunker.chunk("")
    assert result == []


def test_chunk_indices_sequential():
    chunker = TextChunker(max_tokens=10, overlap_tokens=2)
    text = " ".join(["word"] * 30)
    result = chunker.chunk(text)
    for i, chunk in enumerate(result):
        assert chunk.index == i
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_rag_chunker.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement TextChunker**

Create `backend/app/rag/chunker.py`:
```python
from dataclasses import dataclass

MERGE_THRESHOLD = 100  # paragraphs under this word count get merged


@dataclass
class Chunk:
    text: str
    index: int


class TextChunker:
    """Hybrid text chunker: split by paragraphs, merge small, split large."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, text: str) -> list[Chunk]:
        if not text or not text.strip():
            return []

        # Step 1: Split by paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # Step 2: Merge small paragraphs
        merged = self._merge_small(paragraphs)

        # Step 3: Split large blocks
        raw_chunks = []
        for block in merged:
            if self._word_count(block) > self.max_tokens:
                raw_chunks.extend(self._split_large(block))
            else:
                raw_chunks.append(block)

        return [Chunk(text=t, index=i) for i, t in enumerate(raw_chunks)]

    def _word_count(self, text: str) -> int:
        return len(text.split())

    def _merge_small(self, paragraphs: list[str]) -> list[str]:
        if not paragraphs:
            return []

        merged = []
        current = paragraphs[0]

        for para in paragraphs[1:]:
            combined_count = self._word_count(current) + self._word_count(para)
            if self._word_count(current) < MERGE_THRESHOLD and combined_count <= self.max_tokens:
                current = current + "\n\n" + para
            else:
                merged.append(current)
                current = para

        merged.append(current)
        return merged

    def _split_large(self, text: str) -> list[str]:
        """Split a large block by sentences, with overlap."""
        # Split on ". " (sentence boundary) while preserving the period
        parts = text.split(". ")
        sentences = [p + "." for p in parts[:-1]] + [parts[-1]] if len(parts) > 1 else [text]
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current_words = []
        current_count = 0

        for sentence in sentences:
            words = sentence.split()
            if current_count + len(words) > self.max_tokens and current_words:
                chunks.append(" ".join(current_words))
                # Keep overlap
                overlap_words = current_words[-self.overlap_tokens:] if self.overlap_tokens else []
                current_words = overlap_words
                current_count = len(current_words)
            current_words.extend(words)
            current_count += len(words)

        if current_words:
            chunks.append(" ".join(current_words))

        return chunks if chunks else [text]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_rag_chunker.py -v`
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/rag/chunker.py backend/tests/test_rag_chunker.py
git commit -m "feat(rag): add hybrid text chunker with paragraph merge and overlap split"
```

---

### Task 4: Content extractors with registry

**Files:**
- Create: `backend/app/rag/extractors/__init__.py`
- Create: `backend/app/rag/extractors/base.py`
- Create: `backend/app/rag/extractors/txt_extractor.py`
- Create: `backend/app/rag/extractors/pdf_extractor.py`
- Create: `backend/app/rag/extractors/issue_extractor.py`
- Create: `backend/tests/test_rag_extractors.py`

- [ ] **Step 1: Write failing tests for the registry and extractors**

Create `backend/tests/test_rag_extractors.py`:
```python
import os
import tempfile

from app.rag.extractors.base import ExtractedContent, ExtractorRegistry
from app.rag.extractors.txt_extractor import TxtExtractor
from app.rag.extractors.issue_extractor import IssueExtractor


def test_extracted_content_dataclass():
    ec = ExtractedContent(title="Test", text="Hello", metadata={"key": "val"})
    assert ec.title == "Test"
    assert ec.text == "Hello"
    assert ec.metadata == {"key": "val"}


def test_registry_register_and_get():
    registry = ExtractorRegistry()
    extractor = TxtExtractor()
    registry.register(extractor)
    assert registry.get("text/plain") is extractor


def test_registry_supports():
    registry = ExtractorRegistry()
    registry.register(TxtExtractor())
    assert registry.supports("text/plain") is True
    assert registry.supports("application/pdf") is False


def test_registry_get_unknown_returns_none():
    registry = ExtractorRegistry()
    assert registry.get("application/unknown") is None


def test_txt_extractor():
    extractor = TxtExtractor()
    assert extractor.source_type == "file"
    assert "text/plain" in extractor.supported_mimetypes
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello world\n\nSecond paragraph")
        f.flush()
        result = extractor.extract(f.name, original_name="test.txt")
    os.unlink(f.name)
    assert result.title == "test.txt"
    assert "Hello world" in result.text
    assert "Second paragraph" in result.text


def test_issue_extractor():
    extractor = IssueExtractor()
    assert extractor.source_type == "issue"
    issue_data = {
        "name": "Login Feature",
        "specification": "Spec content here",
        "plan": "Plan content here",
        "recap": "Recap content here",
    }
    result = extractor.extract(issue_data)
    assert result.title == "Login Feature"
    assert "## Specification" in result.text
    assert "Spec content here" in result.text
    assert "## Plan" in result.text
    assert "## Recap" in result.text


def test_issue_extractor_missing_fields():
    extractor = IssueExtractor()
    issue_data = {"name": "Partial Issue", "specification": "Only spec"}
    result = extractor.extract(issue_data)
    assert result.title == "Partial Issue"
    assert "Only spec" in result.text
    # plan and recap are missing, should not appear
    assert "## Plan" not in result.text
    assert "## Recap" not in result.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_rag_extractors.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement base classes**

Create `backend/app/rag/extractors/__init__.py` (empty).

Create `backend/app/rag/extractors/base.py`:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractedContent:
    title: str
    text: str
    metadata: dict = field(default_factory=dict)


class ContentExtractor(ABC):
    """Base class for content extractors."""

    source_type: str  # "file" or "issue"
    supported_mimetypes: list[str] = []

    @abstractmethod
    def extract(self, source, **kwargs) -> ExtractedContent:
        """Extract text content from a source."""


class ExtractorRegistry:
    """Registry mapping MIME types to extractors."""

    def __init__(self):
        self._extractors: dict[str, ContentExtractor] = {}

    def register(self, extractor: ContentExtractor):
        for mime in extractor.supported_mimetypes:
            self._extractors[mime] = extractor

    def get(self, mimetype: str) -> ContentExtractor | None:
        return self._extractors.get(mimetype)

    def supports(self, mimetype: str) -> bool:
        return mimetype in self._extractors
```

- [ ] **Step 4: Implement TxtExtractor**

Create `backend/app/rag/extractors/txt_extractor.py`:
```python
from app.rag.extractors.base import ContentExtractor, ExtractedContent


class TxtExtractor(ContentExtractor):
    source_type = "file"
    supported_mimetypes = ["text/plain"]

    def extract(self, source: str, **kwargs) -> ExtractedContent:
        """Extract text from a plain text file. source = file path."""
        original_name = kwargs.get("original_name", "unknown.txt")
        with open(source, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        return ExtractedContent(
            title=original_name,
            text=text,
            metadata={"mime_type": "text/plain"},
        )
```

- [ ] **Step 5: Implement PdfExtractor**

Create `backend/app/rag/extractors/pdf_extractor.py`:
```python
from pypdf import PdfReader

from app.rag.extractors.base import ContentExtractor, ExtractedContent


class PdfExtractor(ContentExtractor):
    source_type = "file"
    supported_mimetypes = ["application/pdf"]

    def extract(self, source: str, **kwargs) -> ExtractedContent:
        """Extract text from a PDF file. source = file path."""
        original_name = kwargs.get("original_name", "unknown.pdf")
        reader = PdfReader(source)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())
        return ExtractedContent(
            title=original_name,
            text="\n\n".join(pages),
            metadata={"mime_type": "application/pdf", "page_count": len(reader.pages)},
        )
```

- [ ] **Step 6: Implement IssueExtractor**

Create `backend/app/rag/extractors/issue_extractor.py`:
```python
from app.rag.extractors.base import ContentExtractor, ExtractedContent


class IssueExtractor(ContentExtractor):
    source_type = "issue"
    supported_mimetypes = []  # Not MIME-based

    def extract(self, source: dict, **kwargs) -> ExtractedContent:
        """Extract text from issue data dict. source = {name, specification, plan, recap}."""
        sections = []
        for field, header in [
            ("specification", "## Specification"),
            ("plan", "## Plan"),
            ("recap", "## Recap"),
        ]:
            value = source.get(field)
            if value and value.strip():
                sections.append(f"{header}\n\n{value.strip()}")

        return ExtractedContent(
            title=source.get("name") or "Untitled Issue",
            text="\n\n".join(sections),
            metadata={"source_type": "issue"},
        )
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_rag_extractors.py -v`
Expected: 7 PASSED

- [ ] **Step 8: Commit**

```bash
git add backend/app/rag/extractors/ backend/tests/test_rag_extractors.py
git commit -m "feat(rag): add content extractors with registry pattern (txt, pdf, issue)"
```

---

### Task 5: LanceDB vector store wrapper

**Files:**
- Create: `backend/app/rag/store.py`
- Create: `backend/tests/test_rag_store.py`
- Delete: `backend/app/lancedb_store.py`

- [ ] **Step 1: Write failing tests for the vector store**

Create `backend/tests/test_rag_store.py`:
```python
import tempfile
import os

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_rag_store.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement VectorStore**

Create `backend/app/rag/store.py`:
```python
import json
import logging
from pathlib import Path

import lancedb
import pyarrow as pa

logger = logging.getLogger(__name__)

TABLE_NAME = "project_context_chunks"


class VectorStore:
    """LanceDB wrapper for chunk storage, search, and retrieval."""

    def __init__(self, db_path: str, dimension: int = 384):
        path = Path(db_path)
        path.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(path))
        self._dimension = dimension
        self._table = None

    def _get_schema(self) -> pa.Schema:
        return pa.schema([
            pa.field("id", pa.string()),
            pa.field("project_id", pa.string()),
            pa.field("chunk_text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), self._dimension)),
            pa.field("source_type", pa.string()),
            pa.field("source_id", pa.string()),
            pa.field("title", pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("total_chunks", pa.int32()),
            pa.field("metadata", pa.string()),
            pa.field("created_at", pa.string()),
        ])

    def _get_table(self):
        if self._table is None:
            try:
                self._table = self._db.open_table(TABLE_NAME)
            except Exception:
                self._table = self._db.create_table(
                    TABLE_NAME, schema=self._get_schema()
                )
        return self._table

    def add(self, records: list[dict]):
        table = self._get_table()
        table.add(records)

    def delete_by_source(self, source_id: str):
        table = self._get_table()
        table.delete(f"source_id = '{source_id}'")

    VALID_SOURCE_TYPES = {"file", "issue"}

    def search(
        self,
        query_vector: list[float],
        project_id: str,
        source_type: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        table = self._get_table()
        where = f"project_id = '{project_id}'"
        if source_type:
            if source_type not in self.VALID_SOURCE_TYPES:
                return []
            where += f" AND source_type = '{source_type}'"

        try:
            results = (
                table.search(query_vector)
                .where(where)
                .metric("cosine")
                .limit(limit)
                .to_list()
            )
        except Exception:
            return []

        return [
            {
                "chunk_id": r["id"],
                "title": r["title"],
                "source_type": r["source_type"],
                "source_id": r["source_id"],
                "project_id": r["project_id"],
                "score": round(1 - r.get("_distance", 0), 4),
                "preview": r["chunk_text"][:200],
            }
            for r in results
        ]

    def get_chunk(self, chunk_id: str, project_id: str) -> dict | None:
        table = self._get_table()
        try:
            results = (
                table.search()
                .where(f"id = '{chunk_id}' AND project_id = '{project_id}'")
                .limit(1)
                .to_list()
            )
        except Exception:
            return None

        if not results:
            return None

        row = results[0]
        source_id = row["source_id"]
        chunk_index = row["chunk_index"]

        # Find adjacent chunks
        previous_id = None
        next_id = None
        try:
            siblings = (
                table.search()
                .where(f"source_id = '{source_id}'")
                .limit(1000)
                .to_list()
            )
            siblings.sort(key=lambda r: r["chunk_index"])
            for i, s in enumerate(siblings):
                if s["id"] == chunk_id:
                    if i > 0:
                        previous_id = siblings[i - 1]["id"]
                    if i < len(siblings) - 1:
                        next_id = siblings[i + 1]["id"]
                    break
        except Exception:
            pass

        metadata = row.get("metadata", "{}")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        return {
            "chunk_id": row["id"],
            "chunk_text": row["chunk_text"],
            "source_type": row["source_type"],
            "source_id": source_id,
            "title": row["title"],
            "chunk_index": chunk_index,
            "total_chunks": row["total_chunks"],
            "metadata": metadata,
            "adjacent_chunks": {
                "previous": previous_id,
                "next": next_id,
            },
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_rag_store.py -v`
Expected: 6 PASSED

- [ ] **Step 5: Delete old lancedb_store.py**

Remove `backend/app/lancedb_store.py` — it's unused (grep the codebase first to confirm no imports).

Run: `cd backend && grep -r "lancedb_store" app/ --include="*.py"` — should return only the file itself.

- [ ] **Step 6: Commit**

```bash
git add backend/app/rag/store.py backend/tests/test_rag_store.py
git rm backend/app/lancedb_store.py
git commit -m "feat(rag): add LanceDB vector store wrapper, remove old stub"
```

---

### Task 6: RAG pipeline orchestrator

**Files:**
- Create: `backend/app/rag/pipeline.py`
- Create: `backend/tests/test_rag_pipeline.py`

- [ ] **Step 1: Write failing tests for the pipeline**

Create `backend/tests/test_rag_pipeline.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_rag_pipeline.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement EmbeddingPipeline**

Create `backend/app/rag/pipeline.py`:
```python
import json
import logging
import uuid
from datetime import datetime, timezone

from app.rag.chunker import TextChunker
from app.rag.drivers.base import EmbeddingDriver
from app.rag.extractors.base import ExtractorRegistry
from app.rag.extractors.issue_extractor import IssueExtractor
from app.rag.store import VectorStore

logger = logging.getLogger(__name__)

_issue_extractor = IssueExtractor()


class EmbeddingPipeline:
    """Orchestrates: extract → chunk → embed → store."""

    def __init__(
        self,
        registry: ExtractorRegistry,
        chunker: TextChunker,
        driver: EmbeddingDriver,
        store: VectorStore,
    ):
        self.registry = registry
        self.chunker = chunker
        self.driver = driver
        self.store = store

    def embed_file(
        self,
        project_id: str,
        source_id: str,
        file_path: str,
        mime_type: str,
        original_name: str,
    ) -> str:
        """Embed a file. Returns 'ok' or 'skipped'."""
        extractor = self.registry.get(mime_type)
        if extractor is None:
            logger.info("No extractor for MIME type %s, skipping %s", mime_type, original_name)
            return "skipped"

        content = extractor.extract(file_path, original_name=original_name)
        self._process(project_id, source_id, content, source_type="file")
        return "ok"

    def embed_issue(self, project_id: str, source_id: str, issue_data: dict) -> str:
        """Embed a completed issue. Returns 'ok'."""
        content = _issue_extractor.extract(issue_data)
        self._process(project_id, source_id, content, source_type="issue")
        return "ok"

    def delete_source(self, source_id: str):
        """Delete all chunks for a source."""
        self.store.delete_by_source(source_id)

    def _process(self, project_id: str, source_id: str, content, source_type: str):
        """Core pipeline: chunk → embed → delete old → store new."""
        chunks = self.chunker.chunk(content.text)
        if not chunks:
            logger.info("No chunks produced for %s/%s", source_type, source_id)
            return

        texts = [c.text for c in chunks]
        vectors = self.driver.embed(texts)
        total = len(chunks)
        now = datetime.now(timezone.utc).isoformat()

        records = [
            {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "chunk_text": chunk.text,
                "vector": vector,
                "source_type": source_type,
                "source_id": source_id,
                "title": content.title,
                "chunk_index": chunk.index,
                "total_chunks": total,
                "metadata": json.dumps(content.metadata),
                "created_at": now,
            }
            for chunk, vector in zip(chunks, vectors)
        ]

        # Delete old chunks then insert new
        self.store.delete_by_source(source_id)
        self.store.add(records)
        logger.info("Embedded %d chunks for %s/%s", total, source_type, source_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_rag_pipeline.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/rag/pipeline.py backend/tests/test_rag_pipeline.py
git commit -m "feat(rag): add embedding pipeline orchestrator"
```

---

### Task 7: RAG service (async integration layer)

**Files:**
- Create: `backend/app/services/rag_service.py`
- Create: `backend/tests/test_rag_service.py`

- [ ] **Step 1: Write failing tests for RAG service**

Create `backend/tests/test_rag_service.py`:
```python
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

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
        original_name="test.txt",
    )
    mock_pipeline.embed_file.assert_called_once()
    mock_event_service.emit.assert_called_once()
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_completed"


async def test_embed_file_skipped(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    mock_pipeline.embed_file.return_value = "skipped"
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/test.docx", mime_type="application/msword",
        original_name="test.docx",
    )
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_skipped"


async def test_embed_issue_async(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_issue(
        project_id="p1", source_id="i1",
        issue_data={"name": "Test", "specification": "spec"},
    )
    mock_pipeline.embed_issue.assert_called_once()


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
        original_name="test.txt",
    )
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_failed"
    assert "extraction failed" in event["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_rag_service.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement RagService**

Create `backend/app/services/rag_service.py`:
```python
import asyncio
import contextlib
import logging
from datetime import datetime, timezone

from app.rag.pipeline import EmbeddingPipeline
from app.services.event_service import EventService

logger = logging.getLogger(__name__)

# Lock per source_id to prevent concurrent re-indexing.
# Uses a counter to clean up locks when no longer in use.
_source_locks: dict[str, tuple[asyncio.Lock, int]] = {}


@contextlib.asynccontextmanager
async def _source_lock(source_id: str):
    """Acquire a per-source lock, cleaning up when no longer needed."""
    if source_id not in _source_locks:
        _source_locks[source_id] = (asyncio.Lock(), 0)
    lock, count = _source_locks[source_id]
    _source_locks[source_id] = (lock, count + 1)
    try:
        async with lock:
            yield
    finally:
        _, count = _source_locks[source_id]
        if count <= 1:
            del _source_locks[source_id]
        else:
            _source_locks[source_id] = (lock, count - 1)


class RagService:
    """Async integration layer between the RAG pipeline and the rest of the app."""

    def __init__(self, pipeline: EmbeddingPipeline, event_service: EventService):
        self.pipeline = pipeline
        self.event_service = event_service

    async def embed_file(
        self,
        project_id: str,
        source_id: str,
        file_path: str,
        mime_type: str,
        original_name: str,
    ):
        """Embed a file asynchronously (runs CPU-bound work in thread)."""
        async with _source_lock(source_id):
            try:
                result = await asyncio.to_thread(
                    self.pipeline.embed_file,
                    project_id=project_id,
                    source_id=source_id,
                    file_path=file_path,
                    mime_type=mime_type,
                    original_name=original_name,
                )
                if result == "skipped":
                    await self.event_service.emit({
                        "type": "embedding_skipped",
                        "source_type": "file",
                        "source_id": source_id,
                        "title": original_name,
                        "reason": f"No extractor for MIME type: {mime_type}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    await self.event_service.emit({
                        "type": "embedding_completed",
                        "source_type": "file",
                        "source_id": source_id,
                        "title": original_name,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception as e:
                logger.exception("Embedding failed for file %s", source_id)
                await self.event_service.emit({
                    "type": "embedding_failed",
                    "source_type": "file",
                    "source_id": source_id,
                    "title": original_name,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    async def embed_issue(self, project_id: str, source_id: str, issue_data: dict):
        """Embed a completed issue asynchronously."""
        title = issue_data.get("name") or "Untitled Issue"
        async with _source_lock(source_id):
            try:
                await asyncio.to_thread(
                    self.pipeline.embed_issue,
                    project_id=project_id,
                    source_id=source_id,
                    issue_data=issue_data,
                )
                await self.event_service.emit({
                    "type": "embedding_completed",
                    "source_type": "issue",
                    "source_id": source_id,
                    "title": title,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.exception("Embedding failed for issue %s", source_id)
                await self.event_service.emit({
                    "type": "embedding_failed",
                    "source_type": "issue",
                    "source_id": source_id,
                    "title": title,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    async def search(
        self,
        query: str,
        project_id: str,
        source_type: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Semantic search across project context."""
        vectors = await asyncio.to_thread(self.pipeline.driver.embed, [query])
        query_vector = vectors[0]
        results = await asyncio.to_thread(
            self.pipeline.store.search,
            query_vector=query_vector,
            project_id=project_id,
            source_type=source_type,
            limit=limit,
        )
        return results

    async def get_chunk_details(self, chunk_id: str, project_id: str) -> dict | None:
        """Get full details of a specific chunk."""
        return await asyncio.to_thread(
            self.pipeline.store.get_chunk, chunk_id, project_id
        )

    async def delete_source(self, source_id: str):
        """Delete all chunks for a source."""
        async with _source_lock(source_id):
            await asyncio.to_thread(self.pipeline.delete_source, source_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_rag_service.py -v`
Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rag_service.py backend/tests/test_rag_service.py
git commit -m "feat(rag): add async RAG service with source locking and event broadcasting"
```

---

### Task 8: Wire up RAG in app lifespan and create singleton

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add RAG initialization to lifespan**

Modify `backend/app/main.py` to initialize the RAG pipeline components on startup:

Add these imports at the top:
```python
from app.config import settings
from app.rag import set_rag_service
from app.rag.chunker import TextChunker
from app.rag.drivers.sentence_transformer import SentenceTransformerDriver
from app.rag.extractors.base import ExtractorRegistry
from app.rag.extractors.txt_extractor import TxtExtractor
from app.rag.extractors.pdf_extractor import PdfExtractor
from app.rag.pipeline import EmbeddingPipeline
from app.rag.store import VectorStore
from app.services.rag_service import RagService
from app.services.event_service import event_service
```

Modify the `lifespan` function to initialize the RAG components:
```python
@asynccontextmanager
async def lifespan(app):
    logger.info("Hook registry: %d event(s) registered", len(hook_registry._hooks))
    for event_type, hooks in hook_registry._hooks.items():
        for h in hooks:
            logger.info("  %s -> %s", event_type.value, h.name)

    # Initialize RAG pipeline
    registry = ExtractorRegistry()
    registry.register(TxtExtractor())
    registry.register(PdfExtractor())

    driver = SentenceTransformerDriver(model_name=settings.embedding_model)
    chunker = TextChunker(
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    store = VectorStore(db_path=settings.lancedb_path)
    pipeline = EmbeddingPipeline(
        registry=registry, chunker=chunker, driver=driver, store=store
    )
    rag_service = RagService(pipeline=pipeline, event_service=event_service)
    set_rag_service(rag_service)
    logger.info("RAG pipeline initialized (driver=%s, model=%s)", settings.embedding_driver, settings.embedding_model)

    async with mcp.session_manager.run():
        yield

    set_rag_service(None)
```

- [ ] **Step 2: Verify the app starts without errors**

Run: `cd backend && python -c "from app.main import app; print('OK')"`
Expected: `OK` (no import errors)

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(rag): wire up RAG pipeline initialization in app lifespan"
```

---

### Task 9: Integrate RAG with file upload and delete

**Files:**
- Modify: `backend/app/routers/files.py`

- [ ] **Step 1: Trigger embedding on file upload**

Modify `backend/app/routers/files.py`:

Add import at top:
```python
import asyncio
from app.rag import get_rag_service
```

Modify the `upload_files` endpoint to trigger embedding after commit:
```python
@router.post("", response_model=list[ProjectFileResponse], status_code=201)
async def upload_files(project_id: str, files: list[UploadFile], db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    try:
        records = await service.upload_files(project_id, files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()

    # Trigger async embedding for each uploaded file
    rag = get_rag_service()
    for record in records:
        file_path = service.get_file_path(project_id, record.stored_name)
        asyncio.create_task(rag.embed_file(
            project_id=project_id,
            source_id=record.id,
            file_path=file_path,
            mime_type=record.mime_type,
            original_name=record.original_name,
        ))

    return [ProjectFileResponse.from_model(r) for r in records]
```

- [ ] **Step 2: Trigger deletion on file delete**

Modify the `delete_file` endpoint:
```python
@router.delete("/{file_id}", status_code=204)
async def delete_file(project_id: str, file_id: str, db: AsyncSession = Depends(get_db)):
    await _check_project(project_id, db)
    service = FileService(db)
    deleted = await service.delete(project_id, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()

    # Remove embeddings for the deleted file
    rag = get_rag_service()
    asyncio.create_task(rag.delete_source(file_id))
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/files.py
git commit -m "feat(rag): trigger embedding on file upload, cleanup on delete"
```

---

### Task 10: Integrate RAG with issue completion

**Files:**
- Modify: `backend/app/mcp/server.py`

- [ ] **Step 1: Trigger embedding when issue is completed**

Modify `backend/app/mcp/server.py`:

Add import at top:
```python
import asyncio
from app.rag import get_rag_service
```

Modify the `complete_issue` tool to trigger embedding. Extract issue data before committing (while session is still open), then fire the background task:
```python
@mcp.tool(description=_desc["tool.complete_issue.description"])
async def complete_issue(project_id: str, issue_id: str, recap: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.complete_issue(issue_id, project_id, recap)
            # Extract data while session is open
            issue_data = {
                "name": issue.name or (issue.description or "")[:100],
                "specification": issue.specification,
                "plan": issue.plan,
                "recap": issue.recap,
            }
            issue_id_val = issue.id
            await session.commit()

            # Trigger async embedding
            rag = get_rag_service()
            asyncio.create_task(rag.embed_issue(
                project_id=project_id,
                source_id=issue_id_val,
                issue_data=issue_data,
            ))

            return {"id": issue_id_val, "status": issue.status.value, "recap": issue.recap}
        except AppError as e:
            return {"error": e.message}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/mcp/server.py
git commit -m "feat(rag): trigger issue embedding on completion"
```

---

### Task 11: MCP search tools

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/app/mcp/default_settings.json`
- Create: `backend/tests/test_mcp_rag_tools.py`

- [ ] **Step 1: Add tool descriptions to default_settings.json**

Add to `backend/app/mcp/default_settings.json`:
```json
"tool.search_project_context.description": "Search project context using semantic similarity. Searches across embedded files and completed issues. Returns a list of matching chunks with preview, score, and source info. Use get_context_chunk_details to get the full text of a result.",
"tool.get_context_chunk_details.description": "Get full details of a specific context chunk found via search_project_context. Returns the complete text, metadata, and links to adjacent chunks for navigation."
```

- [ ] **Step 2: Write failing tests for the MCP tools**

Create `backend/tests/test_mcp_rag_tools.py`:
```python
from unittest.mock import MagicMock, AsyncMock, patch

import pytest


@pytest.fixture
def mock_rag_service():
    svc = MagicMock()
    svc.search = AsyncMock(return_value=[
        {"chunk_id": "c1", "title": "test.txt", "source_type": "file", "score": 0.85, "preview": "hello"}
    ])
    svc.get_chunk_details = AsyncMock(return_value={
        "chunk_id": "c1", "chunk_text": "full text", "source_type": "file",
        "source_id": "f1", "title": "test.txt", "chunk_index": 0,
        "total_chunks": 1, "metadata": {}, "adjacent_chunks": {"previous": None, "next": None},
    })
    return svc


async def test_search_project_context(mock_rag_service):
    with patch("app.mcp.server.get_rag_service", return_value=mock_rag_service):
        from app.mcp.server import search_project_context
        result = await search_project_context(project_id="p1", query="hello")
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["chunk_id"] == "c1"
        mock_rag_service.search.assert_called_once_with(
            query="hello", project_id="p1", source_type=None, limit=5
        )


async def test_search_project_context_with_filters(mock_rag_service):
    with patch("app.mcp.server.get_rag_service", return_value=mock_rag_service):
        from app.mcp.server import search_project_context
        await search_project_context(project_id="p1", query="hello", source_type="file", limit=3)
        mock_rag_service.search.assert_called_once_with(
            query="hello", project_id="p1", source_type="file", limit=3
        )


async def test_get_context_chunk_details(mock_rag_service):
    with patch("app.mcp.server.get_rag_service", return_value=mock_rag_service):
        from app.mcp.server import get_context_chunk_details
        result = await get_context_chunk_details(project_id="p1", chunk_id="c1")
        assert result["chunk_id"] == "c1"
        assert result["chunk_text"] == "full text"


async def test_get_context_chunk_details_not_found(mock_rag_service):
    mock_rag_service.get_chunk_details = AsyncMock(return_value=None)
    with patch("app.mcp.server.get_rag_service", return_value=mock_rag_service):
        from app.mcp.server import get_context_chunk_details
        result = await get_context_chunk_details(project_id="p1", chunk_id="nonexistent")
        assert "error" in result
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_mcp_rag_tools.py -v`
Expected: FAIL

- [ ] **Step 4: Add MCP tools to server.py**

Add at the bottom of `backend/app/mcp/server.py` (before the task tools section or after):
```python
# ── RAG tools (project context search) ─────────────────────────────────────


@mcp.tool(description=_desc["tool.search_project_context.description"])
async def search_project_context(
    project_id: str,
    query: str,
    source_type: str | None = None,
    limit: int = 5,
) -> dict:
    rag = get_rag_service()
    results = await rag.search(
        query=query, project_id=project_id, source_type=source_type, limit=limit
    )
    return {"results": results}


@mcp.tool(description=_desc["tool.get_context_chunk_details.description"])
async def get_context_chunk_details(project_id: str, chunk_id: str) -> dict:
    rag = get_rag_service()
    chunk = await rag.get_chunk_details(chunk_id=chunk_id, project_id=project_id)
    if chunk is None:
        return {"error": "Chunk not found or does not belong to this project"}
    return chunk
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_mcp_rag_tools.py -v`
Expected: 4 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/server.py backend/app/mcp/default_settings.json backend/tests/test_mcp_rag_tools.py
git commit -m "feat(rag): add search_project_context and get_context_chunk_details MCP tools"
```

---

### Task 12: Run full test suite and verify

**Files:** none (verification only)

- [ ] **Step 1: Run all tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass, including existing tests (no regressions)

- [ ] **Step 2: Run the application and verify startup**

Run: `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
Expected: App starts, logs show "RAG pipeline initialized"

- [ ] **Step 3: Commit any remaining fixes**

If any test or startup issues were found, fix them and commit:
```bash
git add -A
git commit -m "fix(rag): address test/startup issues from integration"
```
