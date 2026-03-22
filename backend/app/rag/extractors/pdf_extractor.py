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
