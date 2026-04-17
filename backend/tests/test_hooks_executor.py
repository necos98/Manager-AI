"""Tests for the Claude Code subprocess executor, focusing on timeout cleanup."""
from __future__ import annotations

import os
import sys

from app.hooks.executor import ClaudeCodeExecutor


async def test_executor_times_out_and_terminates_subprocess(tmp_path, monkeypatch):
    """When the `claude` stub outlives the timeout, the executor must
    terminate it and return a timed-out result instead of hanging."""
    sep = os.pathsep
    if sys.platform == "win32":
        stub = tmp_path / "claude.bat"
        stub.write_text(
            "@echo off\r\n"
            'python -c "import time; time.sleep(30)"\r\n'
        )
    else:
        stub = tmp_path / "claude"
        stub.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n")
        stub.chmod(0o755)

    monkeypatch.setenv("PATH", str(tmp_path) + sep + os.environ["PATH"])

    result = await ClaudeCodeExecutor().run(
        prompt="hi", project_path=str(tmp_path), timeout=1
    )
    assert result.success is False
    assert "timed out" in (result.error or "").lower()


async def test_executor_reports_missing_binary(tmp_path, monkeypatch):
    """FileNotFoundError path still returns a clean failure result."""
    monkeypatch.setenv("PATH", str(tmp_path))
    result = await ClaudeCodeExecutor().run(
        prompt="hi", project_path=str(tmp_path), timeout=1
    )
    assert result.success is False
    assert "not found" in (result.error or "").lower()
