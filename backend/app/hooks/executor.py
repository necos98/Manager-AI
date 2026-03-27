"""Claude Code executor: runs `claude` CLI as a subprocess for a given project."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
    ) -> ExecutorResult:
        """
        Spawn `claude` with the given prompt (sent via stdin) and return the result.

        Args:
            prompt:       The prompt text to pass to Claude Code via stdin.
            project_path: Working directory for the subprocess.
            env_vars:     Additional environment variables to inject.
            timeout:      Maximum seconds to wait for the process (default 300).
        """
        env = os.environ.copy()

        # Default Manager AI env vars, sourced from the current environment
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
            "-p",  # pipe/stdin mode — prompt is passed via stdin
            "--allowedTools",
            "mcp__ManagerAi__*",
        ]

        start = time.monotonic()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_path,
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(input=prompt.encode()),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                duration = time.monotonic() - start
                return ExecutorResult(
                    success=False,
                    error=f"Claude Code process timed out after {timeout}s",
                    duration=duration,
                )

            duration = time.monotonic() - start
            stdout = stdout_bytes.decode(errors="replace").strip()
            stderr = stderr_bytes.decode(errors="replace").strip()

            if process.returncode == 0:
                return ExecutorResult(
                    success=True,
                    output=stdout or None,
                    duration=duration,
                )
            else:
                return ExecutorResult(
                    success=False,
                    output=stdout or None,
                    error=stderr or f"Process exited with code {process.returncode}",
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
            logger.error("Claude Code executor failed: %s", exc)
            return ExecutorResult(
                success=False,
                error=str(exc),
                duration=duration,
            )
