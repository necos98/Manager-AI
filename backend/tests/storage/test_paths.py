from pathlib import Path

import pytest

from app.storage import paths


@pytest.fixture
def proj(tmp_path: Path) -> str:
    return str(tmp_path)


def test_manager_ai_root(proj):
    assert paths.manager_ai_root(proj) == Path(proj) / ".manager_ai"


def test_issues_index(proj):
    assert paths.issues_index(proj) == Path(proj) / ".manager_ai" / "issues.yaml"


def test_issues_dir(proj):
    assert paths.issues_dir(proj) == Path(proj) / ".manager_ai" / "issues"


def test_issue_dir(proj):
    assert paths.issue_dir(proj, "abc") == Path(proj) / ".manager_ai" / "issues" / "abc"


def test_issue_yaml(proj):
    assert paths.issue_yaml(proj, "abc") == Path(proj) / ".manager_ai" / "issues" / "abc" / "issue.yaml"


@pytest.mark.parametrize(
    "field,expected",
    [
        ("description", "description.md"),
        ("specification", "specification.md"),
        ("plan", "plan.md"),
        ("recap", "recap.md"),
    ],
)
def test_issue_md(proj, field, expected):
    assert paths.issue_md(proj, "abc", field) == Path(proj) / ".manager_ai" / "issues" / "abc" / expected


def test_issue_md_invalid(proj):
    with pytest.raises(ValueError):
        paths.issue_md(proj, "abc", "bogus")  # type: ignore[arg-type]


def test_issue_feedback_dir(proj):
    assert paths.issue_feedback_dir(proj, "abc") == Path(proj) / ".manager_ai" / "issues" / "abc" / "feedback"


def test_issue_feedback_md(proj):
    assert paths.issue_feedback_md(proj, "abc", "fb1") == Path(proj) / ".manager_ai" / "issues" / "abc" / "feedback" / "fb1.md"


def test_memories_index(proj):
    assert paths.memories_index(proj) == Path(proj) / ".manager_ai" / "memories.yaml"


def test_memories_dir(proj):
    assert paths.memories_dir(proj) == Path(proj) / ".manager_ai" / "memories"


def test_memory_md(proj):
    assert paths.memory_md(proj, "m1") == Path(proj) / ".manager_ai" / "memories" / "m1.md"


def test_files_index(proj):
    assert paths.files_index(proj) == Path(proj) / ".manager_ai" / "files.yaml"


def test_files_dir(proj):
    assert paths.files_dir(proj) == Path(proj) / ".manager_ai" / "files"


def test_file_text_cache(proj):
    assert paths.file_text_cache(proj, "f1") == Path(proj) / ".manager_ai" / "files" / "f1.txt"


def test_resources_dir(proj):
    assert paths.resources_dir(proj) == Path(proj) / ".manager_ai" / "resources"


def test_migration_sentinel(proj):
    assert paths.migration_sentinel(proj) == Path(proj) / ".manager_ai" / ".migration_done"


def test_gitignore(proj):
    assert paths.gitignore(proj) == Path(proj) / ".manager_ai" / ".gitignore"


def test_cache_dir(proj):
    assert paths.cache_dir(proj) == Path(proj) / ".manager_ai" / ".cache"


def test_all_paths_return_pathlib(proj):
    assert isinstance(paths.manager_ai_root(proj), Path)
    assert isinstance(paths.issue_yaml(proj, "x"), Path)
    assert isinstance(paths.memory_md(proj, "x"), Path)
