from __future__ import annotations

from pathlib import Path
from typing import Literal

MarkdownField = Literal["description", "specification", "plan", "recap"]

_MD_FIELDS: frozenset[str] = frozenset({"description", "specification", "plan", "recap"})


def manager_ai_root(project_path: str) -> Path:
    return Path(project_path) / ".manager_ai"


def issues_index(project_path: str) -> Path:
    return manager_ai_root(project_path) / "issues.yaml"


def issues_dir(project_path: str) -> Path:
    return manager_ai_root(project_path) / "issues"


def issue_dir(project_path: str, issue_id: str) -> Path:
    return issues_dir(project_path) / issue_id


def issue_yaml(project_path: str, issue_id: str) -> Path:
    return issue_dir(project_path, issue_id) / "issue.yaml"


def issue_md(project_path: str, issue_id: str, field: MarkdownField) -> Path:
    if field not in _MD_FIELDS:
        raise ValueError(f"Unknown markdown field: {field!r}")
    return issue_dir(project_path, issue_id) / f"{field}.md"


def issue_feedback_dir(project_path: str, issue_id: str) -> Path:
    return issue_dir(project_path, issue_id) / "feedback"


def issue_feedback_md(project_path: str, issue_id: str, feedback_id: str) -> Path:
    return issue_feedback_dir(project_path, issue_id) / f"{feedback_id}.md"


def memories_index(project_path: str) -> Path:
    return manager_ai_root(project_path) / "memories.yaml"


def memories_dir(project_path: str) -> Path:
    return manager_ai_root(project_path) / "memories"


def memory_md(project_path: str, memory_id: str) -> Path:
    return memories_dir(project_path) / f"{memory_id}.md"


def files_index(project_path: str) -> Path:
    return manager_ai_root(project_path) / "files.yaml"


def files_dir(project_path: str) -> Path:
    return manager_ai_root(project_path) / "files"


def file_text_cache(project_path: str, file_id: str) -> Path:
    return files_dir(project_path) / f"{file_id}.txt"


def resources_dir(project_path: str) -> Path:
    return manager_ai_root(project_path) / "resources"


def migration_sentinel(project_path: str) -> Path:
    return manager_ai_root(project_path) / ".migration_done"


def gitignore(project_path: str) -> Path:
    return manager_ai_root(project_path) / ".gitignore"


def cache_dir(project_path: str) -> Path:
    return manager_ai_root(project_path) / ".cache"
