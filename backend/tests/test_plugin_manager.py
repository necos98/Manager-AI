from __future__ import annotations

import asyncio
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
    load_plugins,
    save_plugins,
    set_plugin_enabled,
)
from app.mcp.plugin_client import PluginClient
from app.mcp.plugin_proxy import register_plugin_tools, unregister_plugin_tools
from app.mcp.plugin_manager import PluginManager


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
        cfg = PluginConfig(
            name="test", transport=PluginTransport.stdio, command="echo"
        )
        pf = PluginsFile(plugins={"test": cfg})
        save_plugins(str(tmp_path), pf)

        loaded = load_plugins(str(tmp_path))
        assert "test" in loaded.plugins
        assert loaded.plugins["test"].name == "test"
        assert loaded.plugins["test"].command == "echo"

    def test_invalid_plugin_skipped(self, tmp_path):
        yaml_path = Path(tmp_path) / ".manager_ai" / "plugins.yaml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": 1,
            "plugins": {
                "good": {
                    "name": "good",
                    "transport": "stdio",
                    "command": "echo",
                },
                "bad": {
                    "name": "bad",
                    "transport": "stdio",
                    # missing command
                },
            },
        }
        yaml_path.write_text(yaml.dump(data), encoding="utf-8")

        loaded = load_plugins(str(tmp_path))
        assert "good" in loaded.plugins
        assert "bad" not in loaded.plugins  # invalid → skipped

    def test_set_plugin_enabled(self, tmp_path):
        cfg = PluginConfig(name="test", transport=PluginTransport.stdio, command="echo")
        pf = PluginsFile(plugins={"test": cfg})
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
        "schema_version": 1,
        "plugins": {
            "dummy": {
                "name": "Dummy Test",
                "enabled": True,
                "transport": "stdio",
                "command": "python",
                "args": [dummy_mcp_script_path],
                "access_level": "read_only",
                "timeout": 10,
            }
        },
    }
    yaml_path = manager_ai / "plugins.yaml"
    yaml_path.write_text(yaml.dump(cfg), encoding="utf-8")
    return str(tmp_path)


class TestPluginManagerLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop_plugins(self, plugins_yaml_with_dummy):
        from mcp.server.fastmcp import FastMCP

        mcp_instance = FastMCP("test-mcp")
        manager = PluginManager()
        project_id = "proj-test"
        project_path = plugins_yaml_with_dummy

        await manager.start_plugins_for_project(project_id, project_path, mcp_instance)
        statuses = manager.get_status(project_id)
        assert len(statuses) == 1
        assert statuses[0]["name"] == "dummy"
        assert statuses[0]["connected"] is True
        assert statuses[0]["tool_count"] == 2

        # Verify tools registered on the MCP instance
        tool_names = list(mcp_instance._tool_manager._tools.keys())
        assert "dummy__echo" in tool_names
        assert "dummy__add" in tool_names

        await manager.stop_plugins_for_project(project_id)
        statuses_after = manager.get_status(project_id)
        assert statuses_after == []

    @pytest.mark.asyncio
    async def test_disable_plugin(self, plugins_yaml_with_dummy):
        from mcp.server.fastmcp import FastMCP

        mcp_instance = FastMCP("test-mcp")
        manager = PluginManager()
        project_id = "proj-test"
        project_path = plugins_yaml_with_dummy

        await manager.start_plugins_for_project(project_id, project_path, mcp_instance)
        assert manager.get_status(project_id)[0]["connected"] is True

        await manager.disable_plugin(project_id, project_path, "dummy", mcp_instance)
        assert manager.get_status(project_id) == []

        # Verify YAML was updated
        loaded = load_plugins(project_path)
        assert loaded.plugins["dummy"].enabled is False

    @pytest.mark.asyncio
    async def test_enable_then_disable(self, plugins_yaml_with_dummy):
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
        assert manager.get_status(project_id)[0]["connected"] is True

        # Disable
        ok = await manager.disable_plugin(project_id, project_path, "dummy", mcp_instance)
        assert ok is True
        assert manager.get_status(project_id) == []
