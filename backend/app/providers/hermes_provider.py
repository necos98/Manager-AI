from __future__ import annotations

from app.providers.base import AgentProvider


class HermesProvider(AgentProvider):
    """Provider per Hermes Agent CLI.

    Hermes usa il sottocomando ``chat`` per sessioni interattive.
    I flag ``--yolo`` e ``--worktree`` permettono di bypassare le conferme
    e isolare il lavoro in un worktree.

    A differenza di Claude Code, Hermes torna **due** comandi per ogni
    operazione: il primo avvia la chat, il secondo e' il messaggio
    iniziale. Questo permette interazioni multi-turn (es. fare domande
    via ``ask_user_question`` e ricevere risposte).

    Rispetto a Claude Code, Hermes non ha i comandi built-in ``/run-issue``,
    ``/run-pipeline``, ecc. Questi sono definiti come skill Hermes nel progetto.
    I comandi generati assumono che le skill corrispondenti siano installate.
    """

    @property
    def name(self) -> str:
        return "hermes"

    def build_run_issue_commands(self, issue_id: str) -> list[str]:
        return [
            "hermes chat --skills run-issue --yolo",
            f"Work on issue {issue_id}",
        ]

    def build_run_pipeline_commands(self, issue_id: str) -> list[str]:
        return [
            "hermes chat --skills run-pipeline --yolo",
            f"Execute pipeline step for issue {issue_id}",
        ]

    def build_ask_brainstorm_commands(self, project_id: str) -> list[str]:
        return [
            "hermes chat --skills ask-and-brainstorm --yolo",
            f"Brainstorming for project {project_id}",
        ]

    def build_manage_agent_commands(self, intent: str = "") -> list[str]:
        if intent:
            return [
                "hermes chat --skills manage-agent --yolo",
                intent,
            ]
        return [
            "hermes chat --skills manage-agent --yolo",
        ]

    def build_hook_command(
        self, prompt: str, tool_guidance: str = ""
    ) -> list[str]:
        cmd = ["hermes", "chat", "-q", prompt, "--quiet"]
        if tool_guidance:
            cmd += ["-s", "tool-guidance"]
        return cmd

    @staticmethod
    def build_notification_command(message: str) -> list[str]:
        """Build a hermes chat -q command to send a notification via Telegram.

        The returned list can be passed directly to ``asyncio.create_subprocess_exec``.
        Hermes will invoke ``send_message`` to deliver the notification.
        """
        return ["hermes", "chat", "-q", message, "--quiet"]
