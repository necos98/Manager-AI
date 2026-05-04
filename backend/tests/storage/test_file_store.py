from pathlib import Path

import pytest

from app.storage import atomic, file_store, paths
from app.storage.file_store import FileRecord


def _new_file(
    file_id: str = "f1",
    *,
    original_name: str = "doc.pdf",
    stored_name: str | None = None,
    file_type: str = "pdf",
    file_size: int = 1234,
    mime_type: str = "application/pdf",
    extraction_status: str = "ok",
    extraction_error: str | None = None,
    extracted_at: str | None = "2026-04-01T10:00:00",
    created_at: str = "2026-04-01T10:00:00",
    metadata: dict | None = None,
    extracted_text: str | None = None,
) -> FileRecord:
    return FileRecord(
        id=file_id,
        original_name=original_name,
        stored_name=stored_name or f"{file_id}.{file_type}",
        file_type=file_type,
        file_size=file_size,
        mime_type=mime_type,
        extraction_status=extraction_status,
        extraction_error=extraction_error,
        extracted_at=extracted_at,
        created_at=created_at,
        metadata=metadata,
        extracted_text=extracted_text,
    )


@pytest.fixture
def proj(tmp_path: Path) -> str:
    return str(tmp_path)


def test_create_and_load_file(proj):
    rec = _new_file("f1", original_name="x.pdf")
    file_store.create_file(proj, rec)

    loaded = file_store.load_file(proj, "f1")
    assert loaded is not None
    assert loaded.id == "f1"
    assert loaded.original_name == "x.pdf"


def test_load_missing_file_returns_none(proj):
    assert file_store.load_file(proj, "nope") is None


def test_create_writes_extracted_text_when_present(proj):
    rec = _new_file("f1", extracted_text="hello world")
    file_store.create_file(proj, rec)
    cache_path = paths.file_text_cache(proj, "f1")
    assert cache_path.exists()
    assert cache_path.read_text(encoding="utf-8") == "hello world"


def test_create_skips_text_cache_when_none(proj):
    rec = _new_file("f1", extracted_text=None)
    file_store.create_file(proj, rec)
    assert not paths.file_text_cache(proj, "f1").exists()


def test_load_file_hydrates_extracted_text(proj):
    rec = _new_file("f1", extracted_text="body content")
    file_store.create_file(proj, rec)

    loaded = file_store.load_file(proj, "f1")
    assert loaded.extracted_text == "body content"


def test_list_files_does_not_load_text(proj):
    file_store.create_file(proj, _new_file("f1", extracted_text="big body"))
    listed = file_store.list_files(proj)
    assert len(listed) == 1
    assert listed[0].id == "f1"
    # Light shape
    assert listed[0].extracted_text is None


def test_index_sorted_by_created_at_then_id(proj):
    file_store.create_file(proj, _new_file("late", created_at="2026-04-05T10:00:00"))
    file_store.create_file(proj, _new_file("early", created_at="2026-04-01T10:00:00"))
    file_store.create_file(proj, _new_file("mid", created_at="2026-04-03T10:00:00"))
    index = atomic.read_yaml(paths.files_index(proj))
    assert [e["id"] for e in index["files"]] == ["early", "mid", "late"]


def test_update_file(proj):
    file_store.create_file(proj, _new_file("u1", extraction_status="pending"))
    rec = file_store.load_file(proj, "u1")
    rec.extraction_status = "ok"
    rec.extracted_text = "now extracted"
    rec.extracted_at = "2026-04-02T10:00:00"
    file_store.update_file(proj, rec)

    loaded = file_store.load_file(proj, "u1")
    assert loaded.extraction_status == "ok"
    assert loaded.extracted_text == "now extracted"


def test_update_file_clears_text_when_set_none(proj):
    file_store.create_file(proj, _new_file("u2", extracted_text="body"))
    assert paths.file_text_cache(proj, "u2").exists()

    rec = file_store.load_file(proj, "u2")
    rec.extracted_text = None
    rec.extraction_status = "failed"
    file_store.update_file(proj, rec)
    assert not paths.file_text_cache(proj, "u2").exists()


def test_delete_file(proj):
    file_store.create_file(proj, _new_file("d1", extracted_text="x"))
    file_store.create_file(proj, _new_file("d2"))
    file_store.delete_file(proj, "d1")

    assert file_store.load_file(proj, "d1") is None
    assert not paths.file_text_cache(proj, "d1").exists()
    listed = file_store.list_files(proj)
    assert [f.id for f in listed] == ["d2"]


def test_read_write_extracted_text(proj):
    file_store.write_extracted_text(proj, "f1", "chunk of text")
    assert file_store.read_extracted_text(proj, "f1") == "chunk of text"


def test_read_extracted_text_missing_returns_empty(proj):
    assert file_store.read_extracted_text(proj, "nope") == ""


def test_metadata_preserved(proj):
    rec = _new_file("m1", metadata={"low_text": True, "pages": 5})
    file_store.create_file(proj, rec)
    loaded = file_store.load_file(proj, "m1")
    assert loaded.metadata == {"low_text": True, "pages": 5}


def test_rebuild_files_index_is_idempotent_sort(proj):
    # files.yaml is the source of truth for metadata — rebuild just re-sorts it.
    file_store.create_file(proj, _new_file("r1", created_at="2026-04-01T10:00:00"))
    file_store.create_file(proj, _new_file("r2", created_at="2026-04-02T10:00:00"))
    file_store.rebuild_files_index(proj)
    index = atomic.read_yaml(paths.files_index(proj))
    assert [e["id"] for e in index["files"]] == ["r1", "r2"]


def test_rebuild_files_index_on_missing_index_writes_empty(proj):
    paths.manager_ai_root(proj).mkdir(parents=True, exist_ok=True)
    file_store.rebuild_files_index(proj)
    index = atomic.read_yaml(paths.files_index(proj))
    assert index == {"schema_version": 1, "files": []}
