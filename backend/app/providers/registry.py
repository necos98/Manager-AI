from __future__ import annotations

from app.providers.base import AgentProvider
from app.providers.claude_provider import ClaudeProvider


class AgentProviderRegistry:
    """Registry dei provider disponibili.

    Uso:
        provider = AgentProviderRegistry.get("claude")
        cmd = provider.build_run_pipeline_command("iss-1")
    """

    _providers: dict[str, type[AgentProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[AgentProvider]) -> None:
        if not issubclass(provider_cls, AgentProvider):
            raise TypeError(
                f"{provider_cls.__name__} must subclass AgentProvider"
            )
        cls._providers[name] = provider_cls

    @classmethod
    def get(cls, name: str) -> AgentProvider:
        if name not in cls._providers:
            raise KeyError(
                f"Unknown agent provider: {name!r}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return cls._providers[name]()

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._providers.keys())


def register_builtin_providers() -> None:
    """Registra i provider built-in (chiamato all'avvio dell'app)."""
    AgentProviderRegistry.register("claude", ClaudeProvider)


# Auto-register built-in providers on import
register_builtin_providers()
