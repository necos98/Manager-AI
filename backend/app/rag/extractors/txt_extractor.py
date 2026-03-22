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
