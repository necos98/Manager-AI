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
