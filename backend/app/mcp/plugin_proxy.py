from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import Tool

from app.mcp.plugin_client import PluginClient
from app.mcp.plugin_config import AccessLevel

logger = logging.getLogger(__name__)


def register_plugin_tools(
    mcp: FastMCP,
    plugin_key: str,
    client: PluginClient,
    access_level: AccessLevel,
) -> int:
    """Register proxy tools for a plugin on the FastMCP instance.

    Returns number of tools registered.
    """
    access_tag = f"[{plugin_key} plugin — {access_level.value}]"
    registered = 0

    for tool in client.tools:
        proxy_name = f"{plugin_key}__{tool.name}"
        description = f"{access_tag} {tool.description or ''}".strip()

        fn = _make_proxy_function(proxy_name, tool.name, client)
        mcp.add_tool(fn, name=proxy_name, description=description)
        registered += 1
        logger.info("Registered proxy tool: %s", proxy_name)

    return registered


def _make_proxy_function(
    proxy_name: str,
    tool_name: str,
    client: PluginClient,
) -> Any:
    """Generate an async proxy function using **kwargs without annotations."""
    async def proxy(**kwargs):
        return await client.call_tool(tool_name, kwargs)

    proxy.__name__ = proxy_name
    return proxy


def unregister_plugin_tools(
    mcp: FastMCP,
    plugin_key: str,
    tools: list[Tool],
) -> None:
    """Remove proxy tools for a plugin from the FastMCP instance."""
    for tool in tools:
        proxy_name = f"{plugin_key}__{tool.name}"
        if proxy_name in mcp._tool_manager._tools:
            del mcp._tool_manager._tools[proxy_name]
            logger.info("Unregistered proxy tool: %s", proxy_name)
