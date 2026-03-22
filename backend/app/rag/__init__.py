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
