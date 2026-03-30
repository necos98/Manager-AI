from __future__ import annotations

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
        project_name: str = "",
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
                        "project_id": project_id,
                        "project_name": project_name,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    await self.event_service.emit({
                        "type": "embedding_completed",
                        "source_type": "file",
                        "source_id": source_id,
                        "title": original_name,
                        "project_id": project_id,
                        "project_name": project_name,
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
                    "project_id": project_id,
                    "project_name": project_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    async def embed_issue(self, project_id: str, source_id: str, issue_data: dict, project_name: str = ""):
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
                    "project_id": project_id,
                    "project_name": project_name,
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
                    "project_id": project_id,
                    "project_name": project_name,
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
