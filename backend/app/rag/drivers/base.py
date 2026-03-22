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
