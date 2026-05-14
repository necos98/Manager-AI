from __future__ import annotations

import inspect
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

        fn = _make_proxy_function(proxy_name, tool.name, client, tool)
        mcp.add_tool(fn, name=proxy_name, description=description)
        registered += 1
        logger.info("Registered proxy tool: %s", proxy_name)

    return registered


def _make_proxy_function(
    proxy_name: str,
    tool_name: str,
    client: PluginClient,
    tool: Tool,
) -> Any:
    """Generate an async proxy with parameters from the plugin tool's inputSchema.

    Uses the real parameter names and types so FastMCP generates the correct
    JSON Schema — no double-wrapped kwargs bug.
    """
    input_schema = getattr(tool, "inputSchema", {}) or {}
    properties = input_schema.get("properties", {})
    required: set[str] = set(input_schema.get("required", []))

    # Build inspect.Parameter list from schema
    params: list[inspect.Parameter] = []
    for name in properties:
        if not name.isidentifier():
            continue
        default = inspect.Parameter.empty if name in required else None
        params.append(
            inspect.Parameter(
                name=name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=inspect.Parameter.empty,
                default=default,
            )
        )

    # If schema has no properties, fall back to generic **kwargs
    if not params:
        async def _fallback(**kwargs: object) -> dict:
            return await client.call_tool(tool_name, kwargs)
        _fallback.__name__ = proxy_name
        _fallback.__signature__ = inspect.Signature([])  # type: ignore[attr-defined]
        return _fallback

    # Build signature and function dynamically
    sig = inspect.Signature(params)

    async def _proxy(*_args: object, **_kwargs: object) -> dict:
        bound = sig.bind(*_args, **_kwargs)
        bound.apply_defaults()
        flat = dict(bound.arguments)
        # Drop optional params that were not provided
        flat = {k: v for k, v in flat.items() if v is not None}
        return await client.call_tool(tool_name, flat)

    _proxy.__name__ = proxy_name
    _proxy.__signature__ = sig  # type: ignore[attr-defined]
    return _proxy


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
