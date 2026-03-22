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
