"""Claude Code executor: runs `claude` CLI as a subprocess for a given project."""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _terminate_tree(proc: subprocess.Popen) -> None:
    """Kill `proc` and its process tree. SIGTERM first, SIGKILL after 5s."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            if sys.platform == "win32":
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass


@dataclass
class ExecutorResult:
    success: bool
    output: str | None = None
    error: str | None = None
    duration: float = 0.0


class ClaudeCodeExecutor:
    """Runs a Claude Code prompt in the context of a project directory."""

    async def run(
        self,
        prompt: str,
        project_path: str,
        env_vars: dict | None = None,
        timeout: int = 300,
        tool_guidance: str = "",
    ) -> ExecutorResult:
        """
        Spawn `claude` with the given prompt (sent via stdin) and return the result.

        Uses asyncio.to_thread + subprocess.run to avoid asyncio event loop
        compatibility issues (e.g. SelectorEventLoop on Windows).

        Args:
            prompt:        The prompt text to pass to Claude Code via stdin.
            project_path:  Working directory for the subprocess.
            env_vars:      Additional environment variables to inject.
            timeout:       Maximum seconds to wait for the process (default 300).
            tool_guidance: Optional [Tool guidance] block prepended to the prompt.
        """
        if tool_guidance:
            prompt = tool_guidance + "\n\n" + prompt

        env = os.environ.copy()

        env.setdefault(
            "MANAGER_AI_PROJECT_ID",
            os.environ.get("MANAGER_AI_PROJECT_ID", ""),
        )
        env.setdefault(
            "MANAGER_AI_BASE_URL",
            os.environ.get("MANAGER_AI_BASE_URL", "http://localhost:8000"),
        )

        if env_vars:
            env.update(env_vars)

        cmd = [
            "claude",
            "-p",
            "--allowedTools",
            "mcp__ManagerAi__*",
        ]

        cwd = project_path or None
        prompt_bytes = prompt.encode()
        start = time.monotonic()

        def _run() -> tuple[int, bytes, bytes]:
            popen_kwargs: dict = {
                "stdin": subprocess.PIPE,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "cwd": cwd,
                "env": env,
            }
            if sys.platform == "win32":
                # New process group lets us send CTRL_BREAK_EVENT to the tree.
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs["start_new_session"] = True

            proc = subprocess.Popen(cmd, **popen_kwargs)
            try:
                stdout_b, stderr_b = proc.communicate(
                    input=prompt_bytes, timeout=timeout
                )
                return proc.returncode, stdout_b, stderr_b
            except subprocess.TimeoutExpired:
                _terminate_tree(proc)
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
                raise

        try:
            returncode, stdout_b, stderr_b = await asyncio.to_thread(_run)
            duration = time.monotonic() - start
            stdout = stdout_b.decode(errors="replace").strip()
            stderr = stderr_b.decode(errors="replace").strip()

            if returncode == 0:
                return ExecutorResult(success=True, output=stdout or None, duration=duration)
            else:
                return ExecutorResult(
                    success=False,
                    output=stdout or None,
                    error=stderr or f"Process exited with code {returncode}",
                    duration=duration,
                )

        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            return ExecutorResult(
                success=False,
                error=f"Claude Code process timed out after {timeout}s",
                duration=duration,
            )
        except FileNotFoundError:
            duration = time.monotonic() - start
            logger.error("'claude' CLI not found on PATH")
            return ExecutorResult(
                success=False,
                error="'claude' executable not found. Ensure Claude Code CLI is installed and on PATH.",
                duration=duration,
            )
        except Exception as exc:  # noqa: BLE001
            duration = time.monotonic() - start
            logger.error("Claude Code executor failed: %s", exc, exc_info=True)
            return ExecutorResult(
                success=False,
                error=str(exc) or type(exc).__name__,
                duration=duration,
            )
