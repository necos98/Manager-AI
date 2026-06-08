from __future__ import annotations

import shlex

from app.providers.base import AgentProvider


class HermesProvider(AgentProvider):
    """Provider per Hermes Agent CLI.

    Hermes usa il sottocomando ``chat`` per sessioni interattive e il flag
    ``-z`` per chiamate one-shot (hook). I flag ``--yolo`` e ``--worktree``
    permettono di bypassare le conferme e isolare il lavoro in un worktree.

    Rispetto a Claude Code, Hermes non ha i comandi built-in ``/run-issue``,
    ``/run-pipeline``, ecc. Questi sono definiti come skill Hermes nel progetto.
    I comandi generati assumono che le skill corrispondenti siano installate.
    """

    @property
    def name(self) -> str:
        return "hermes"

    def build_run_issue_command(self, issue_id: str) -> str:
        return (
            f"hermes chat --skills run-issue --worktree --yolo "
            f"-q \"Work on issue {shlex.quote(issue_id)}\""
        )

    def build_run_pipeline_command(self, issue_id: str) -> str:
        return (
            f"hermes chat --skills run-pipeline --worktree --yolo "
            f"-q \"Execute pipeline step for issue {shlex.quote(issue_id)}\""
        )

    def build_ask_brainstorm_command(self, project_id: str) -> str:
        return (
            f"hermes chat --skills ask-and-brainstorm --yolo "
            f"-q \"Brainstorming for project {shlex.quote(project_id)}\""
        )

    def build_manage_agent_command(self, intent: str = "") -> str:
        base = (
            "hermes chat --skills manage-agent --yolo"
        )
        if intent:
            base += f" -q {shlex.quote(intent)}"
        return base

    def build_hook_command(
        self, prompt: str, tool_guidance: str = ""
    ) -> list[str]:
        cmd = ["hermes", "chat", "-q", prompt, "--quiet"]
        if tool_guidance:
            cmd += ["-s", "tool-guidance"]
        return cmd
