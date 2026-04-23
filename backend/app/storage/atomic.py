from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_yaml(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    text = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        width=4096,
        default_flow_style=False,
    )
    _atomic_write_text(path, text)


def read_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}
    return yaml.safe_load(raw) or {}


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    _atomic_write_text(path, content)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def cleanup_tmp_files(root: Path) -> None:
    if not root.exists():
        return
    for tmp in root.rglob("*.tmp"):
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _atomic_write_text(path: Path, content: str) -> None:
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
