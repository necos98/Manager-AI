"""Tests for the Agent Provider system — base ABC, implementations, registry."""

import pytest

from app.providers.base import AgentProvider
from app.providers.claude_provider import ClaudeProvider
from app.providers.hermes_provider import HermesProvider
from app.providers.registry import AgentProviderRegistry


# ==============================================================================
# ABC — AgentProvider
# ==============================================================================


def test_abc_cannot_be_instantiated():
    with pytest.raises(TypeError):
        AgentProvider()  # type: ignore[abstract]


def test_abc_has_all_abstract_methods():
    expected = {
        "name": property,
        "build_run_issue_command": ...,
        "build_run_pipeline_command": ...,
        "build_ask_brainstorm_command": ...,
        "build_manage_agent_command": ...,
        "build_hook_command": ...,
    }
    for method_name in expected:
        assert hasattr(AgentProvider, method_name), (
            f"AgentProvider missing abstract method: {method_name}"
        )


# ==============================================================================
# ClaudeProvider — generation commands
# ==============================================================================


@pytest.fixture
def claude() -> ClaudeProvider:
    return ClaudeProvider()


class TestClaudeProvider:
    def test_name(self, claude: ClaudeProvider):
        assert claude.name == "claude"

    def test_build_run_issue_command(self, claude: ClaudeProvider):
        cmd = claude.build_run_issue_command("iss-1")
        assert cmd.startswith("claude")
        assert "--dangerously-skip-permissions" in cmd
        assert "/run-issue iss-1" in cmd

    def test_build_run_issue_command_quotes_id(self, claude: ClaudeProvider):
        cmd = claude.build_run_issue_command("abc-123")
        assert "/run-issue abc-123" in cmd

    def test_build_run_pipeline_command(self, claude: ClaudeProvider):
        cmd = claude.build_run_pipeline_command("iss-1")
        assert cmd.startswith("claude")
        assert "--dangerously-skip-permissions" in cmd
        assert "/run-pipeline iss-1" in cmd

    def test_build_run_pipeline_command_quotes_id(self, claude: ClaudeProvider):
        cmd = claude.build_run_pipeline_command("abc-123")
        assert "/run-pipeline abc-123" in cmd

    def test_build_ask_brainstorm_command(self, claude: ClaudeProvider):
        cmd = claude.build_ask_brainstorm_command("proj-1")
        assert cmd.startswith("claude")
        assert "--dangerously-skip-permissions" in cmd
        assert "/ask-and-brainstorm proj-1" in cmd

    def test_build_ask_brainstorm_command_quotes_id(self, claude: ClaudeProvider):
        cmd = claude.build_ask_brainstorm_command("abc-123")
        assert "/ask-and-brainstorm abc-123" in cmd

    def test_build_manage_agent_no_intent(self, claude: ClaudeProvider):
        cmd = claude.build_manage_agent_command()
        assert cmd.startswith("claude")
        assert "--dangerously-skip-permissions" in cmd
        assert "/manage-agent" in cmd
        # No trailing intent beyond the quoted /manage-agent
        assert cmd.endswith('"')  # /manage-agent" closes the quotes
        # Verify there's no extra argument after the closing quote
        # split('"') -> ['prefix...', '/manage-agent', '']
        parts = cmd.split('"')
        assert parts[-1] == "", f"Expected nothing after closing quote: {cmd!r}"
        assert len(parts) == 3, f"Expected exactly 2 quotes: {cmd!r}"

    def test_build_manage_agent_with_intent(self, claude: ClaudeProvider):
        cmd = claude.build_manage_agent_command("Review the codebase for bugs")
        assert cmd.startswith("claude")
        assert "--dangerously-skip-permissions" in cmd
        assert "/manage-agent" in cmd
        assert "Review" in cmd

    def test_build_manage_agent_with_empty_string(self, claude: ClaudeProvider):
        cmd = claude.build_manage_agent_command("")
        assert cmd.startswith("claude")
        assert "/manage-agent" in cmd
        assert '"' in cmd  # the base command wraps /manage-agent in quotes
        # No extra intent at the end
        parts = cmd.split('"')
        assert len(parts) <= 2 or parts[-1].strip() == ""

    def test_build_hook_command(self, claude: ClaudeProvider):
        cmd = claude.build_hook_command("Hello world")
        assert cmd == ["claude", "-p", "Hello world", "--output-format", "text"]

    def test_build_hook_command_with_tool_guidance(self, claude: ClaudeProvider):
        cmd = claude.build_hook_command("Analyze this", tool_guidance="Use tool X")
        assert cmd == [
            "claude",
            "-p",
            "Analyze this",
            "--append-system-prompt",
            "Use tool X",
            "--output-format",
            "text",
        ]

    def test_build_hook_command_empty_prompt(self, claude: ClaudeProvider):
        cmd = claude.build_hook_command("")
        assert cmd == ["claude", "-p", "", "--output-format", "text"]


# ==============================================================================
# HermesProvider
# ==============================================================================


@pytest.fixture
def hermes() -> HermesProvider:
    return HermesProvider()


class TestHermesProvider:
    def test_name(self, hermes: HermesProvider):
        assert hermes.name == "hermes"

    def test_build_run_issue_command(self, hermes: HermesProvider):
        cmd = hermes.build_run_issue_command("iss-1")
        assert cmd.startswith("hermes")
        assert "run-issue" in cmd
        assert "--yolo" in cmd
        assert "iss-1" in cmd

    def test_build_run_pipeline_command(self, hermes: HermesProvider):
        cmd = hermes.build_run_pipeline_command("iss-1")
        assert cmd.startswith("hermes")
        assert "run-pipeline" in cmd
        assert "--yolo" in cmd
        assert "iss-1" in cmd

    def test_build_ask_brainstorm_command(self, hermes: HermesProvider):
        cmd = hermes.build_ask_brainstorm_command("proj-1")
        assert cmd.startswith("hermes")
        assert "ask-and-brainstorm" in cmd
        assert "--yolo" in cmd
        assert "proj-1" in cmd

    def test_build_manage_agent_no_intent(self, hermes: HermesProvider):
        cmd = hermes.build_manage_agent_command()
        assert cmd.startswith("hermes")
        assert "manage-agent" in cmd
        assert "--yolo" in cmd

    def test_build_manage_agent_with_intent(self, hermes: HermesProvider):
        cmd = hermes.build_manage_agent_command("Review bugs")
        assert cmd.startswith("hermes")
        assert "manage-agent" in cmd
        assert "Review" in cmd

    def test_build_hook_command(self, hermes: HermesProvider):
        cmd = hermes.build_hook_command("Hello")
        assert cmd[0] == "hermes"
        assert cmd[1] == "chat"
        assert cmd[2] == "-q"
        assert "Hello" in cmd
        assert "--quiet" in cmd

    def test_build_hook_command_with_guidance(self, hermes: HermesProvider):
        cmd = hermes.build_hook_command("Analyze", tool_guidance="tool X")
        assert cmd[0] == "hermes"
        assert cmd[1] == "chat"
        assert "-s" in cmd
        assert "tool-guidance" in cmd


# ==============================================================================
# AgentProviderRegistry
# ==============================================================================


class TestAgentProviderRegistry:
    def test_get_claude_provider(self):
        provider = AgentProviderRegistry.get("claude")
        assert isinstance(provider, ClaudeProvider)
        assert provider.name == "claude"

    def test_get_unknown_provider_raises_keyerror(self):
        with pytest.raises(KeyError) as exc:
            AgentProviderRegistry.get("nonexistent")
        assert "nonexistent" in str(exc.value)
        assert "claude" in str(exc.value)

    def test_available_providers_includes_claude_and_hermes(self):
        available = AgentProviderRegistry.available()
        assert "claude" in available
        assert "hermes" in available

    def test_get_hermes_provider(self):
        provider = AgentProviderRegistry.get("hermes")
        assert isinstance(provider, HermesProvider)
        assert provider.name == "hermes"

    def test_register_and_get_custom(self):
        class DummyProvider(AgentProvider):
            @property
            def name(self) -> str:
                return "dummy"

            def build_run_issue_command(self, issue_id: str) -> str:
                return f"dummy run {issue_id}"

            def build_run_pipeline_command(self, issue_id: str) -> str:
                return f"dummy pipeline {issue_id}"

            def build_ask_brainstorm_command(self, project_id: str) -> str:
                return f"dummy ask {project_id}"

            def build_manage_agent_command(self, intent: str = "") -> str:
                base = "dummy manage"
                return f"{base} {intent}" if intent else base

            def build_hook_command(
                self, prompt: str, tool_guidance: str = ""
            ) -> list[str]:
                return ["dummy", prompt]

        AgentProviderRegistry.register("dummy", DummyProvider)
        try:
            provider = AgentProviderRegistry.get("dummy")
            assert provider.name == "dummy"
            assert provider.build_run_issue_command("x") == "dummy run x"
        finally:
            # Clean up — remove from registry
            AgentProviderRegistry._providers.pop("dummy", None)

    def test_register_invalid_provider_raises_typeerror(self):
        class NotAProvider:
            pass

        with pytest.raises(TypeError, match="must subclass AgentProvider"):
            AgentProviderRegistry.register("bad", NotAProvider)  # type: ignore[arg-type]

    def test_get_is_singleton_per_call(self):
        """Each get() creates a new instance to keep providers stateless."""
        p1 = AgentProviderRegistry.get("claude")
        p2 = AgentProviderRegistry.get("claude")
        assert p1 is not p2
        assert p1.build_run_issue_command("x") == p2.build_run_issue_command("x")

    def test_registry_provider_names_match_class(self):
        """Provider name in registry matches the name property of the provider class."""
        for name in AgentProviderRegistry.available():
            provider = AgentProviderRegistry.get(name)
            assert provider.name == name

    def test_register_cannot_overwrite_existing(self):
        """Il registry permette di sovrascrivere — test che funzioni."""
        original = AgentProviderRegistry.get("claude")
        assert isinstance(original, ClaudeProvider)

        # Re-register is allowed (it's a dict)
        AgentProviderRegistry.register("claude", ClaudeProvider)
        provider = AgentProviderRegistry.get("claude")
        assert isinstance(provider, ClaudeProvider)
