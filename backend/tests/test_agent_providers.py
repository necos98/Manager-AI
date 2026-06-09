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
        "build_run_issue_commands": ...,
        "build_run_pipeline_commands": ...,
        "build_ask_brainstorm_commands": ...,
        "build_manage_agent_commands": ...,
        "build_hook_command": ...,
    }
    for method_name in expected:
        assert hasattr(AgentProvider, method_name), (
            f"AgentProvider missing abstract method: {method_name}"
        )


# ==============================================================================
# ClaudeProvider — generation commands (plural, list[str])
# ==============================================================================


@pytest.fixture
def claude() -> ClaudeProvider:
    return ClaudeProvider()


class TestClaudeProvider:
    def test_name(self, claude: ClaudeProvider):
        assert claude.name == "claude"

    def test_build_run_issue_commands(self, claude: ClaudeProvider):
        cmds = claude.build_run_issue_commands("iss-1")
        assert isinstance(cmds, list)
        assert len(cmds) == 1
        assert cmds[0].startswith("claude")
        assert "--dangerously-skip-permissions" in cmds[0]
        assert "/run-issue iss-1" in cmds[0]

    def test_build_run_issue_commands_quotes_id(self, claude: ClaudeProvider):
        cmds = claude.build_run_issue_commands("abc-123")
        assert "/run-issue abc-123" in cmds[0]

    def test_build_run_pipeline_commands(self, claude: ClaudeProvider):
        cmds = claude.build_run_pipeline_commands("iss-1")
        assert isinstance(cmds, list)
        assert len(cmds) == 1
        assert cmds[0].startswith("claude")
        assert "--dangerously-skip-permissions" in cmds[0]
        assert "/run-pipeline iss-1" in cmds[0]

    def test_build_run_pipeline_commands_quotes_id(self, claude: ClaudeProvider):
        cmds = claude.build_run_pipeline_commands("abc-123")
        assert "/run-pipeline abc-123" in cmds[0]

    def test_build_ask_brainstorm_commands(self, claude: ClaudeProvider):
        cmds = claude.build_ask_brainstorm_commands("proj-1")
        assert isinstance(cmds, list)
        assert len(cmds) == 1
        assert cmds[0].startswith("claude")
        assert "--dangerously-skip-permissions" in cmds[0]
        assert "/ask-and-brainstorm proj-1" in cmds[0]

    def test_build_ask_brainstorm_commands_quotes_id(self, claude: ClaudeProvider):
        cmds = claude.build_ask_brainstorm_commands("abc-123")
        assert "/ask-and-brainstorm abc-123" in cmds[0]

    def test_build_manage_agent_commands_no_intent(self, claude: ClaudeProvider):
        cmds = claude.build_manage_agent_commands()
        assert isinstance(cmds, list)
        assert len(cmds) == 1
        assert cmds[0].startswith("claude")
        assert "--dangerously-skip-permissions" in cmds[0]
        assert "/manage-agent" in cmds[0]
        # No trailing intent beyond the quoted /manage-agent
        assert cmds[0].endswith('"')  # /manage-agent" closes the quotes
        parts = cmds[0].split('"')
        assert parts[-1] == "", f"Expected nothing after closing quote: {cmds[0]!r}"
        assert len(parts) == 3, f"Expected exactly 2 quotes: {cmds[0]!r}"

    def test_build_manage_agent_commands_with_intent(self, claude: ClaudeProvider):
        cmds = claude.build_manage_agent_commands("Review the codebase for bugs")
        assert isinstance(cmds, list)
        assert len(cmds) == 1
        assert cmds[0].startswith("claude")
        assert "--dangerously-skip-permissions" in cmds[0]
        assert "/manage-agent" in cmds[0]
        assert "Review" in cmds[0]

    def test_build_manage_agent_commands_with_empty_string(self, claude: ClaudeProvider):
        cmds = claude.build_manage_agent_commands("")
        assert isinstance(cmds, list)
        assert len(cmds) == 1
        assert cmds[0].startswith("claude")
        assert "/manage-agent" in cmds[0]
        assert '"' in cmds[0]  # the base command wraps /manage-agent in quotes
        parts = cmds[0].split('"')
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

    def test_build_run_issue_commands(self, hermes: HermesProvider):
        cmds = hermes.build_run_issue_commands("iss-1")
        assert isinstance(cmds, list)
        assert len(cmds) == 2
        assert cmds[0].startswith("hermes")
        assert "run-issue" in cmds[0]
        assert "--yolo" in cmds[0]
        assert "-q" not in cmds[0], "Hermes should NOT use -q in interactive mode"
        assert "iss-1" in cmds[1]
        assert "Work on issue" in cmds[1]

    def test_build_run_pipeline_commands(self, hermes: HermesProvider):
        cmds = hermes.build_run_pipeline_commands("iss-1")
        assert isinstance(cmds, list)
        assert len(cmds) == 2
        assert cmds[0].startswith("hermes")
        assert "run-pipeline" in cmds[0]
        assert "--yolo" in cmds[0]
        assert "-q" not in cmds[0]
        assert "iss-1" in cmds[1]

    def test_build_ask_brainstorm_commands(self, hermes: HermesProvider):
        cmds = hermes.build_ask_brainstorm_commands("proj-1")
        assert isinstance(cmds, list)
        assert len(cmds) == 2
        assert cmds[0].startswith("hermes")
        assert "ask-and-brainstorm" in cmds[0]
        assert "--yolo" in cmds[0]
        assert "-q" not in cmds[0]
        assert "proj-1" in cmds[1]

    def test_build_manage_agent_commands_no_intent(self, hermes: HermesProvider):
        cmds = hermes.build_manage_agent_commands()
        assert isinstance(cmds, list)
        assert len(cmds) == 1
        assert cmds[0].startswith("hermes")
        assert "manage-agent" in cmds[0]
        assert "--yolo" in cmds[0]
        assert "-q" not in cmds[0]

    def test_build_manage_agent_commands_with_intent(self, hermes: HermesProvider):
        cmds = hermes.build_manage_agent_commands("Review bugs")
        assert isinstance(cmds, list)
        assert len(cmds) == 2
        assert cmds[0].startswith("hermes")
        assert "manage-agent" in cmds[0]
        assert "--yolo" in cmds[0]
        assert "-q" not in cmds[0]
        assert "Review bugs" in cmds[1]

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

            def build_run_issue_commands(self, issue_id: str) -> list[str]:
                return [f"dummy run {issue_id}"]

            def build_run_pipeline_commands(self, issue_id: str) -> list[str]:
                return [f"dummy pipeline {issue_id}"]

            def build_ask_brainstorm_commands(self, project_id: str) -> list[str]:
                return [f"dummy ask {project_id}"]

            def build_manage_agent_commands(self, intent: str = "") -> list[str]:
                base = "dummy manage"
                return [f"{base} {intent}"] if intent else [base]

            def build_hook_command(
                self, prompt: str, tool_guidance: str = ""
            ) -> list[str]:
                return ["dummy", prompt]

        AgentProviderRegistry.register("dummy", DummyProvider)
        try:
            provider = AgentProviderRegistry.get("dummy")
            assert provider.name == "dummy"
            cmds = provider.build_run_issue_commands("x")
            assert cmds == ["dummy run x"]
        finally:
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
        cmds1 = p1.build_run_issue_commands("x")
        cmds2 = p2.build_run_issue_commands("x")
        assert cmds1 == cmds2

    def test_registry_provider_names_match_class(self):
        """Provider name in registry matches the name property of the provider class."""
        for name in AgentProviderRegistry.available():
            provider = AgentProviderRegistry.get(name)
            assert provider.name == name

    def test_register_cannot_overwrite_existing(self):
        """Il registry permette di sovrascrivere — test che funzioni."""
        original = AgentProviderRegistry.get("claude")
        assert isinstance(original, ClaudeProvider)

        AgentProviderRegistry.register("claude", ClaudeProvider)
        provider = AgentProviderRegistry.get("claude")
        assert isinstance(provider, ClaudeProvider)
