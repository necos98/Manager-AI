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
