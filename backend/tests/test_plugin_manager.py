from __future__ import annotations

import asyncio
import contextlib
import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from app.mcp.plugin_config import (
    AccessLevel,
    PluginConfig,
    PluginTransport,
    PluginsFile,
    ProjectPluginConfig,
    load_plugins,
    save_plugins,
    set_plugin_enabled,
)
from app.mcp.plugin_client import PluginClient
from app.mcp.plugin_proxy import register_plugin_tools, unregister_plugin_tools
from app.mcp.plugin_manager import PluginManager
from app.mcp.catalog import catalog_loader, CatalogPlugin, OptionDef


# ── PluginConfig model tests ─────────────────────────────────────────────────


class TestPluginConfig:
    def test_valid_stdio_config(self):
        cfg = PluginConfig(
            name="mysql",
            transport=PluginTransport.stdio,
            command="uvx",
            args=["mcp-server-mysql"],
        )
        assert cfg.transport == PluginTransport.stdio
        assert cfg.command == "uvx"

    def test_valid_http_config(self):
        cfg = PluginConfig(
            name="slack",
            transport=PluginTransport.http,
            url="https://mcp-slack.internal/sse",
        )
        assert cfg.transport == PluginTransport.http
        assert cfg.url == "https://mcp-slack.internal/sse"

    def test_stdio_requires_command(self):
        with pytest.raises(ValueError, match="stdio transport requires 'command'"):
            PluginConfig(name="bad", transport=PluginTransport.stdio, command="")

    def test_http_requires_url(self):
        with pytest.raises(ValueError, match="http transport requires 'url'"):
            PluginConfig(name="bad", transport=PluginTransport.http, url="")

    def test_defaults(self):
        cfg = PluginConfig(name="test", command="echo")
        assert cfg.enabled is True
        assert cfg.transport == PluginTransport.stdio
        assert cfg.access_level == AccessLevel.read_only
        assert cfg.timeout == 30
        assert cfg.args == []
        assert cfg.env == {}
        assert cfg.url == ""

    def test_to_description_tag(self):
        cfg = PluginConfig(name="mysql", transport=PluginTransport.stdio, command="x")
        tag = cfg.to_description_tag()
        assert "mysql" in tag
        assert "read_only" in tag

    def test_tool_prefix(self):
        cfg = PluginConfig(name="test", command="x")
        assert cfg.tool_prefix("mysql") == "mysql__"


# ── YAML load/save tests ────────────────────────────────────────────────────


class TestPluginsYaml:
    def test_load_empty(self, tmp_path):
        plugins_file = load_plugins(str(tmp_path))
        assert plugins_file.plugins == {}

    def test_save_and_load(self, tmp_path):
        proj_cfg = ProjectPluginConfig(enabled=True, config={"KEY": "val"})
        pf = PluginsFile(plugins={"test": proj_cfg})
        save_plugins(str(tmp_path), pf)

        loaded = load_plugins(str(tmp_path))
        assert "test" in loaded.plugins
        assert loaded.plugins["test"].enabled is True
        assert loaded.plugins["test"].config == {"KEY": "val"}

    def test_save_and_load_v1_migration(self, tmp_path):
        """V1 format plugins.yaml is migrated to v2 on load."""
        yaml_path = Path(tmp_path) / ".manager_ai" / "plugins.yaml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": 1,
            "plugins": {
                "legacy": {
                    "name": "Legacy Plugin",
                    "enabled": True,
                    "transport": "stdio",
                    "command": "echo",
                    "args": [],
                    "env": {"HOST": "localhost"},
                    "access_level": "read_only",
                    "timeout": 30,
                },
            },
        }
        yaml_path.write_text(yaml.dump(data), encoding="utf-8")
        loaded = load_plugins(str(tmp_path))
        assert "legacy" in loaded.plugins
        assert loaded.plugins["legacy"].enabled is True
        assert loaded.plugins["legacy"].config == {"HOST": "localhost"}

    def test_invalid_plugin_skipped(self, tmp_path):
        yaml_path = Path(tmp_path) / ".manager_ai" / "plugins.yaml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": 2,
            "plugins": {
                "good": {
                    "enabled": True,
                    "config": {},
                },
                "bad": "not_a_dict",
            },
        }
        yaml_path.write_text(yaml.dump(data), encoding="utf-8")

        loaded = load_plugins(str(tmp_path))
        assert "good" in loaded.plugins
        assert "bad" not in loaded.plugins  # invalid → skipped

    def test_set_plugin_enabled(self, tmp_path):
        proj_cfg = ProjectPluginConfig(enabled=True, config={})
        pf = PluginsFile(plugins={"test": proj_cfg})
        save_plugins(str(tmp_path), pf)

        assert set_plugin_enabled(str(tmp_path), "test", False) is True
        loaded = load_plugins(str(tmp_path))
        assert loaded.plugins["test"].enabled is False

    def test_set_plugin_enabled_missing(self, tmp_path):
        assert set_plugin_enabled(str(tmp_path), "nonexistent", False) is False


# ── PluginManager tests ─────────────────────────────────────────────────────


DUMMY_MCP_SCRIPT = '''
import sys
import json

def read_msg():
    line = sys.stdin.readline()
    if not line:
        sys.exit(0)
    return json.loads(line)

def send_response(msg):
    sys.stdout.write(json.dumps(msg) + "\\n")
    sys.stdout.flush()

while True:
    req = read_msg()
    method = req.get("method", "")
    rid = req.get("id", 0)

    if method == "initialize":
        send_response({"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "dummy", "version": "1.0"},
            "capabilities": {"tools": {}}
        }})
    elif method == "notifications/initialized":
        pass  # no response for notifications
    elif method == "tools/list":
        send_response({"jsonrpc": "2.0", "id": rid, "result": {
            "tools": [
                {"name": "echo", "description": "Echo a message",
                 "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}},
                {"name": "add", "description": "Add two numbers",
                 "inputSchema": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}},
            ]
        }})
    elif method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        if tool_name == "echo":
            send_response({"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": f"echo: {args.get('message', '')}"}]
            }})
        elif tool_name == "add":
            a = args.get("a", 0)
            b_val = args.get("b", 0)
            send_response({"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": str(a + b_val)}]
            }})
        else:
            send_response({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "Unknown tool"}})
    else:
        send_response({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown method: {method}"}})
'''


@pytest.fixture
def dummy_mcp_script_path(tmp_path):
    script = tmp_path / "dummy_mcp.py"
    script.write_text(DUMMY_MCP_SCRIPT, encoding="utf-8")
    return str(script)


class TestPluginClientDummy:
    @pytest.mark.asyncio
    async def test_connect_and_discover_tools(self, dummy_mcp_script_path):
        client = PluginClient(
            plugin_name="dummy",
            transport="stdio",
            command="python",
            args=[dummy_mcp_script_path],
        )
        try:
            await client.connect()
            assert client.connected is True
            assert len(client.tools) == 2
            tool_names = {t.name for t in client.tools}
            assert "echo" in tool_names
            assert "add" in tool_names
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_call_tool(self, dummy_mcp_script_path):
        client = PluginClient(
            plugin_name="dummy",
            transport="stdio",
            command="python",
            args=[dummy_mcp_script_path],
        )
        try:
            await client.connect()
            result = await client.call_tool("echo", {"message": "hello"})
            assert "echo: hello" in result.get("content", "")
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_call_tool_add(self, dummy_mcp_script_path):
        client = PluginClient(
            plugin_name="dummy",
            transport="stdio",
            command="python",
            args=[dummy_mcp_script_path],
        )
        try:
            await client.connect()
            result = await client.call_tool("add", {"a": 3, "b": 4})
            assert "7" in result.get("content", "")
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self, dummy_mcp_script_path):
        client = PluginClient(
            plugin_name="dummy",
            transport="stdio",
            command="python",
            args=[dummy_mcp_script_path],
        )
        await client.connect()
        assert client.connected is True
        await client.disconnect()
        assert client.connected is False
        assert client.tools == []

    @pytest.mark.asyncio
    async def test_call_tool_when_disconnected_raises(self):
        client = PluginClient(plugin_name="offline", transport="stdio", command="echo")
        with pytest.raises(RuntimeError, match="not connected"):
            await client.call_tool("anything", {})

    @pytest.mark.asyncio
    async def test_invalid_command_fails_gracefully(self):
        client = PluginClient(
            plugin_name="bad",
            transport="stdio",
            command="nonexistent_command_xyz",
        )
        with pytest.raises(Exception):
            await client.connect()


class TestPluginConnectError:
    @pytest.mark.asyncio
    async def test_http_unreachable_raises(self):
        client = PluginClient(
            plugin_name="bad-http",
            transport="http",
            url="http://127.0.0.1:19999/does-not-exist",
            timeout=2,
        )
        with pytest.raises(Exception):
            await client.connect()


# ── PluginManager lifecycle tests ────────────────────────────────────────────


@pytest.fixture
def plugins_yaml_with_dummy(tmp_path, dummy_mcp_script_path):
    manager_ai = tmp_path / ".manager_ai"
    manager_ai.mkdir(parents=True, exist_ok=True)
    cfg = {
        "schema_version": 2,
        "plugins": {
            "dummy": {
                "enabled": True,
                "config": {},
            }
        },
    }
    yaml_path = manager_ai / "plugins.yaml"
    yaml_path.write_text(yaml.dump(cfg), encoding="utf-8")
    return str(tmp_path)


@pytest.fixture
def catalog_entry_dummy(dummy_mcp_script_path):
    """Inject a catalog entry for the dummy test plugin, then clean up."""
    cat = CatalogPlugin(
        key="dummy",
        name="Dummy Test",
        description="Test plugin",
        transport=PluginTransport.stdio,
        command="python",
        args=[dummy_mcp_script_path],
        access_level=AccessLevel.read_only,
        timeout=10,
    )
    catalog_loader._plugins["dummy"] = cat
    yield cat
    catalog_loader._plugins.pop("dummy", None)


class TestPluginManagerLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop_plugins(self, plugins_yaml_with_dummy, catalog_entry_dummy):
        from mcp.server.fastmcp import FastMCP

        mcp_instance = FastMCP("test-mcp")
        manager = PluginManager()
        project_id = "proj-test"
        project_path = plugins_yaml_with_dummy

        await manager.start_plugins_for_project(project_id, project_path, mcp_instance)
        statuses = manager.get_status(project_id)
        assert len(statuses) == 1
        assert statuses[0]["name"] == "dummy"
        assert statuses[0]["connected"] is False  # lazy: zero connect at startup
        assert statuses[0]["tool_count"] == 1      # gateway only

        # Verify gateway tool registered on the MCP instance
        tool_names = list(mcp_instance._tool_manager._tools.keys())
        assert "dummy__call" in tool_names

        await manager.stop_plugins_for_project(project_id)
        statuses_after = manager.get_status(project_id)
        assert statuses_after == []

    @pytest.mark.asyncio
    async def test_disable_plugin(self, plugins_yaml_with_dummy, catalog_entry_dummy):
        from mcp.server.fastmcp import FastMCP

        mcp_instance = FastMCP("test-mcp")
        manager = PluginManager()
        project_id = "proj-test"
        project_path = plugins_yaml_with_dummy

        await manager.start_plugins_for_project(project_id, project_path, mcp_instance)
        assert manager.get_status(project_id)[0]["connected"] is False  # lazy

        await manager.disable_plugin(project_id, project_path, "dummy", mcp_instance)
        assert manager.get_status(project_id) == []

        # Verify YAML was updated
        loaded = load_plugins(project_path)
        assert loaded.plugins["dummy"].enabled is False

    @pytest.mark.asyncio
    async def test_enable_then_disable(self, plugins_yaml_with_dummy, catalog_entry_dummy):
        from mcp.server.fastmcp import FastMCP

        mcp_instance = FastMCP("test-mcp")
        manager = PluginManager()
        project_id = "proj-test"
        project_path = plugins_yaml_with_dummy

        # Disable first (update YAML)
        set_plugin_enabled(project_path, "dummy", False)

        # Enable via manager
        ok = await manager.enable_plugin(project_id, project_path, "dummy", mcp_instance)
        assert ok is True
        assert manager.get_status(project_id)[0]["connected"] is False  # lazy

        # Disable
        ok = await manager.disable_plugin(project_id, project_path, "dummy", mcp_instance)
        assert ok is True
        assert manager.get_status(project_id) == []


# ── ensure_connected coordination tests ────────────────────────────────────────


class TestEnsureConnectedCoordination:
    @pytest.mark.asyncio
    async def test_returns_immediately_when_already_connected(self):
        """_connected=True -> ensure_connected() returns without waiting."""
        client = PluginClient(
            plugin_name="test",
            transport="stdio",
            command="echo",
            connect_timeout=5,
        )
        client._connected = True
        client._connect_ready.set()
        client._connect_done.set()

        # Should return immediately — no exception, no delay
        await asyncio.wait_for(client.ensure_connected(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_raises_when_pre_connect_still_running(self):
        """Pre-connect task not done -> RuntimeError, no crash."""
        client = PluginClient(
            plugin_name="test",
            transport="stdio",
            command="echo",
            connect_timeout=1,  # short so test is fast
        )
        # Simulate pre-connect task that never finishes
        async def never_finish():
            await asyncio.Event().wait()
        client._pre_connect_task = asyncio.create_task(never_finish())

        with pytest.raises(RuntimeError, match="still initializing"):
            await client.ensure_connected()

        # Cleanup: cancel the never-finishing task
        client._pre_connect_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await client._pre_connect_task

    @pytest.mark.asyncio
    async def test_own_connect_when_pre_connect_failed(self):
        """Pre-connect task done (failed) -> tries own connect()."""
        client = PluginClient(
            plugin_name="test",
            transport="stdio",
            command="echo",
            connect_timeout=0.5,
        )
        # Simulate failed pre-connect: task done with exception
        async def fail():
            raise RuntimeError("boom")
        task = asyncio.create_task(fail())
        with contextlib.suppress(RuntimeError):
            await task
        client._pre_connect_task = task

        # Mock connect to verify it's called (instead of relying on
        # real connect which depends on OS-specific subprocess behavior).
        connect_called = False

        async def mock_connect():
            nonlocal connect_called
            connect_called = True
            client._connected = True
            client._connect_ready.set()

        client.connect = mock_connect  # type: ignore[method-assign]

        await client.ensure_connected()
        assert connect_called, "own connect() should have been called after pre-connect failure"
        assert client._connected is True

    @pytest.mark.asyncio
    async def test_connect_timeout_raises_runtime_error(self):
        """connect() takes > connect_timeout -> RuntimeError."""
        client = PluginClient(
            plugin_name="test",
            transport="stdio",
            command="echo",
            connect_timeout=0.2,
        )
        # Mock connect to hang forever.  Assigning a plain function to
        # client.connect means self.connect() calls it without implicit
        # self — no binding issues.
        async def slow_connect():
            await asyncio.Event().wait()

        client.connect = slow_connect  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="connection timed out"):
            await client.ensure_connected()
