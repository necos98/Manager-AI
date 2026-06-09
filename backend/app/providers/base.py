from __future__ import annotations

from abc import ABC, abstractmethod


class AgentProvider(ABC):
    """Interfaccia per provider di coding agent CLI.

    Ogni provider (Claude Code, Hermes, etc.) implementa questi metodi
    per generare i comandi corretti per ogni scenario di spawn.

    I metodi ``build_*_commands()`` tornano ``list[str]`` invece di una
    singola stringa perche' alcuni provider (Hermes) richiedono piu'
    scritture nel PTY: comando d'avvio + messaggio iniziale.
    Il chiamante itera sulla lista e scrive ogni elemento nel PTY.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome univoco del provider (es. 'claude', 'hermes')."""
        ...

    @abstractmethod
    def build_run_issue_commands(self, issue_id: str) -> list[str]:
        """Comandi per eseguire una issue (scritti nel PTY del terminale).

        Il chiamante itera sulla lista e scrive ogni elemento nel PTY.
        Per Claude:  [``claude ... "/run-issue abc-123"``]
        Per Hermes:  [``hermes chat --skills run-issue ...``, ``Work on issue abc-123``]
        """
        ...

    @abstractmethod
    def build_run_pipeline_commands(self, issue_id: str) -> list[str]:
        """Comandi per eseguire uno step di pipeline (scritti nel PTY)."""
        ...

    @abstractmethod
    def build_ask_brainstorm_commands(self, project_id: str) -> list[str]:
        """Comandi per Ask & Brainstorm (scritti nel PTY)."""
        ...

    @abstractmethod
    def build_manage_agent_commands(self, intent: str = "") -> list[str]:
        """Comandi per Manage Agent (scritti nel PTY).

        Se intent è fornito, può essere incluso come comando separato.
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
