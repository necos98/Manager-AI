from __future__ import annotations

from abc import ABC, abstractmethod


class AgentProvider(ABC):
    """Interfaccia per provider di coding agent CLI.

    Ogni provider (Claude Code, Hermes, etc.) implementa questi metodi
    per generare i comandi corretti per ogni scenario di spawn.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome univoco del provider (es. 'claude', 'hermes')."""
        ...

    @abstractmethod
    def build_run_issue_command(self, issue_id: str) -> str:
        """Comando per eseguire una issue (scritto nel PTY del terminale).

        Esempio output (Claude):
          claude --dangerously-skip-permissions "/run-issue abc-123"
        """
        ...

    @abstractmethod
    def build_run_pipeline_command(self, issue_id: str) -> str:
        """Comando per eseguire uno step di pipeline (scritto nel PTY).

        Esempio output (Claude):
          claude --dangerously-skip-permissions "/run-pipeline abc-123"
        """
        ...

    @abstractmethod
    def build_ask_brainstorm_command(self, project_id: str) -> str:
        """Comando per Ask & Brainstorm (scritto nel PTY).

        Esempio output (Claude):
          claude --dangerously-skip-permissions "/ask-and-brainstorm proj-1"
        """
        ...

    @abstractmethod
    def build_manage_agent_command(self, intent: str = "") -> str:
        """Comando per Manage Agent (scritto nel PTY).

        Esempio output (Claude):
          claude --dangerously-skip-permissions "/manage-agent"

        Se intent è fornito, viene aggiunto come argomento finale.
        """
        ...

    @abstractmethod
    def build_hook_command(
        self, prompt: str, tool_guidance: str = ""
    ) -> list[str]:
        """Comando per hook subprocess (ritorna lista args per
        asyncio.create_subprocess_exec).

        Esempio output (Claude):
          ["claude", "-p", prompt, "--output-format", "text"]
        """
        ...
