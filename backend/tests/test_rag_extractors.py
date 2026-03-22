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


def test_txt_extractor_supports_markdown():
    extractor = TxtExtractor()
    assert "text/markdown" in extractor.supported_mimetypes
    registry = ExtractorRegistry()
    registry.register(extractor)
    assert registry.get("text/markdown") is extractor

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Heading\n\nSome **bold** text")
        f.flush()
        result = extractor.extract(f.name, original_name="README.md")
    os.unlink(f.name)
    assert result.title == "README.md"
    assert "# Heading" in result.text
    assert "**bold**" in result.text


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
