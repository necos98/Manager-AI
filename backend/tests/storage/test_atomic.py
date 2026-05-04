from pathlib import Path

import pytest

from app.storage import atomic


def test_ensure_dir_creates_nested(tmp_path: Path):
    target = tmp_path / "a" / "b" / "c"
    atomic.ensure_dir(target)
    assert target.is_dir()


def test_ensure_dir_idempotent(tmp_path: Path):
    target = tmp_path / "x"
    atomic.ensure_dir(target)
    atomic.ensure_dir(target)  # no error
    assert target.is_dir()


def test_write_read_yaml_roundtrip(tmp_path: Path):
    path = tmp_path / "data.yaml"
    data = {"schema_version": 1, "items": [{"id": "a", "name": "Foo"}]}
    atomic.write_yaml(path, data)
    assert atomic.read_yaml(path) == data


def test_read_yaml_missing_returns_empty(tmp_path: Path):
    path = tmp_path / "nope.yaml"
    assert atomic.read_yaml(path) == {}


def test_write_yaml_preserves_unicode(tmp_path: Path):
    path = tmp_path / "u.yaml"
    data = {"title": "Città — café 北京"}
    atomic.write_yaml(path, data)
    content = path.read_text(encoding="utf-8")
    assert "Città" in content
    assert "北京" in content
    assert atomic.read_yaml(path) == data


def test_write_yaml_atomic_no_tmp_leftover(tmp_path: Path):
    path = tmp_path / "atomic.yaml"
    atomic.write_yaml(path, {"x": 1})
    # no stray *.tmp in parent
    tmps = list(tmp_path.glob("*.tmp"))
    assert tmps == []


def test_write_yaml_creates_parent(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "out.yaml"
    atomic.write_yaml(path, {"k": "v"})
    assert path.read_text(encoding="utf-8")


def test_write_read_text_roundtrip(tmp_path: Path):
    path = tmp_path / "body.md"
    body = "# Title\n\nLine with unicode é\nMultiline.\n"
    atomic.write_text(path, body)
    assert atomic.read_text(path) == body


def test_read_text_missing_returns_empty_string(tmp_path: Path):
    assert atomic.read_text(tmp_path / "nope.md") == ""


def test_remove_if_exists_present(tmp_path: Path):
    path = tmp_path / "gone.txt"
    path.write_text("x")
    atomic.remove_if_exists(path)
    assert not path.exists()


def test_remove_if_exists_missing(tmp_path: Path):
    # Does not raise
    atomic.remove_if_exists(tmp_path / "nope.txt")


def test_cleanup_tmp_files_removes_only_tmp(tmp_path: Path):
    (tmp_path / "a.yaml").write_text("keep")
    (tmp_path / "a.yaml.tmp").write_text("stale")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md.tmp").write_text("stale nested")
    (sub / "b.md").write_text("keep nested")

    atomic.cleanup_tmp_files(tmp_path)

    assert (tmp_path / "a.yaml").exists()
    assert not (tmp_path / "a.yaml.tmp").exists()
    assert (sub / "b.md").exists()
    assert not (sub / "b.md.tmp").exists()


def test_write_yaml_overwrites_existing(tmp_path: Path):
    path = tmp_path / "o.yaml"
    atomic.write_yaml(path, {"v": 1})
    atomic.write_yaml(path, {"v": 2})
    assert atomic.read_yaml(path) == {"v": 2}


def test_write_yaml_handles_stale_tmp(tmp_path: Path):
    """A leftover *.tmp from a crashed previous write must not block a new write."""
    path = tmp_path / "c.yaml"
    tmp = Path(str(path) + ".tmp")
    tmp.write_text("stale garbage")
    atomic.write_yaml(path, {"ok": True})
    assert atomic.read_yaml(path) == {"ok": True}


def test_yaml_multiline_string(tmp_path: Path):
    path = tmp_path / "ml.yaml"
    data = {"body": "line1\nline2\nline3"}
    atomic.write_yaml(path, data)
    assert atomic.read_yaml(path)["body"] == "line1\nline2\nline3"
