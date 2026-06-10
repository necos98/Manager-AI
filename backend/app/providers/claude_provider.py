from __future__ import annotations

import shlex

from app.providers.base import AgentProvider


class ClaudeProvider(AgentProvider):
    """Provider per Claude Code CLI.

    Genera comandi con il formato attuale:
      claude --dangerously-skip-permissions "/<modalità> <args>"
    """

    @property
    def name(self) -> str:
        return "claude"

    def build_run_issue_commands(self, issue_id: str) -> list[str]:
        return [
            f'claude --dangerously-skip-permissions '
            f'"/run-issue {shlex.quote(issue_id)}"'
        ]

    def build_run_pipeline_commands(self, issue_id: str) -> list[str]:
        return [
            f'claude --dangerously-skip-permissions '
            f'"/run-pipeline {shlex.quote(issue_id)}"'
        ]

    def build_ask_brainstorm_commands(self, project_id: str) -> list[str]:
        return [
            f'claude --dangerously-skip-permissions '
            f'"/ask-and-brainstorm {shlex.quote(project_id)}"'
        ]

    def build_manage_agent_commands(self, intent: str = "") -> list[str]:
        base = (
            'claude --dangerously-skip-permissions '
            '"/manage-agent"'
        )
        if intent:
            base += f" {shlex.quote(intent)}"
        return [base]

    def build_hook_command(
        self, prompt: str, tool_guidance: str = ""
    ) -> list[str]:
        cmd = ["claude", "-p", prompt]
        if tool_guidance:
            cmd += ["--append-system-prompt", tool_guidance]
        cmd += ["--output-format", "text"]
        return cmd
