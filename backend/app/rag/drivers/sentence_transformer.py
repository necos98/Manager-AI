from __future__ import annotations

from app.rag.drivers.base import EmbeddingDriver

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment,misc]

BATCH_SIZE = 32


class SentenceTransformerDriver(EmbeddingDriver):
    """Embedding driver using sentence-transformers (local, CPU-based)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            if SentenceTransformer is None:
                raise ImportError(
                    "sentence-transformers is not installed. "
                    "Run: pip install sentence-transformers"
                )
            self._model = SentenceTransformer(self._model_name)

    @property
    def dimension(self) -> int:
        self._load_model()
        return self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load_model()
        embeddings = self._model.encode(texts, batch_size=BATCH_SIZE)
        return [vec.tolist() for vec in embeddings]
