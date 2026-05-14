from __future__ import annotations

import inspect
import logging
from typing import Any, Optional

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

    proxy_names = []
    for tool in client.tools:
        proxy_name = f"{plugin_key}__{tool.name}"
        description = f"{access_tag} {tool.description or ''}".strip()

        fn = _make_proxy_function(proxy_name, tool.name, client, tool)
        mcp.add_tool(fn, name=proxy_name, description=description)
        proxy_names.append(proxy_name)
        registered += 1
        logger.info("Registered proxy tool: %s", proxy_name)

    client.set_registered_proxy_names(proxy_names)
    return registered


def register_plugin_tools_from_schemas(
    mcp: FastMCP,
    plugin_key: str,
    client: PluginClient,
    access_level: AccessLevel,
    schemas: list[dict],
) -> int:
    """Register proxy tools from saved schemas (client may be disconnected).

    Proxy functions call client.ensure_connected() before delegating,
    so the plugin process is spawned lazily on first use.
    """
    access_tag = f"[{plugin_key} plugin — {access_level.value}]"
    registered = 0

    proxy_names = []
    for schema in schemas:
        tool_name = schema["name"]
        proxy_name = f"{plugin_key}__{tool_name}"
        description = access_tag

        fn = _make_proxy_function(proxy_name, tool_name, client, schema)
        mcp.add_tool(fn, name=proxy_name, description=description)
        proxy_names.append(proxy_name)
        registered += 1
        logger.info("Registered proxy tool (lazy): %s", proxy_name)

    client.set_registered_proxy_names(proxy_names)
    return registered


def _make_proxy_function(
    proxy_name: str,
    tool_name: str,
    client: PluginClient,
    tool_or_schema: Tool | dict,
) -> Any:
    """Generate an async proxy with parameters from the plugin tool's inputSchema.

    Accepts either a Tool object (eager) or a schema dict (lazy).
    Before calling the tool, ensures the client is connected (auto-connect on first use).
    """
    if isinstance(tool_or_schema, dict):
        input_schema = tool_or_schema.get("inputSchema", {}) or {}
    else:
        input_schema = getattr(tool_or_schema, "inputSchema", {}) or {}

    properties = input_schema.get("properties", {})
    required: set[str] = set(input_schema.get("required", []))

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

    if not params:
        async def _fallback(**kwargs: object) -> dict:
            await client.ensure_connected()
            return await client.call_tool(tool_name, kwargs)
        _fallback.__name__ = proxy_name
        _fallback.__signature__ = inspect.Signature([])  # type: ignore[attr-defined]
        return _fallback

    sig = inspect.Signature(params)

    async def _proxy(*_args: object, **_kwargs: object) -> dict:
        await client.ensure_connected()
        bound = sig.bind(*_args, **_kwargs)
        bound.apply_defaults()
        flat = dict(bound.arguments)
        flat = {k: v for k, v in flat.items() if v is not None}
        return await client.call_tool(tool_name, flat)

    _proxy.__name__ = proxy_name
    _proxy.__signature__ = sig  # type: ignore[attr-defined]
    return _proxy


def register_plugin_gateway(
    mcp: FastMCP,
    plugin_key: str,
    client: PluginClient,
    access_level: AccessLevel,
    plugin_description: str = "",
) -> int:
    """Register a single gateway tool per plugin. Zero process spawn at startup.

    The gateway ({plugin}__call) auto-connects on first use, then delegates
    to the real plugin tool. No connection attempt until a tool is called.

    Returns 1.
    """
    access_tag = f"[{plugin_key} plugin — {access_level.value}]"
    proxy_name = f"{plugin_key}__call"
    description = f"{access_tag} {plugin_description}".strip()

    async def _gateway(tool_name: str, arguments: Optional[dict] = None) -> dict:
        try:
            await client.ensure_connected()
        except BaseException as exc:
            logger.error("Plugin %s connect/ensure failed in gateway: %s", plugin_key, exc)
            return {"error": f"Plugin {plugin_key} connection failed: {exc}"}
        try:
            return await client.call_tool(tool_name, arguments or {})
        except BaseException as exc:
            logger.error("Plugin %s call_tool failed in gateway: %s", plugin_key, exc)
            return {"error": f"Plugin {plugin_key} tool call failed: {exc}"}

    _gateway.__name__ = proxy_name
    # Avoid string annotations from __future__ — FastMCP needs real types
    _gateway.__signature__ = inspect.Signature([
        inspect.Parameter("tool_name", inspect.Parameter.KEYWORD_ONLY, annotation=str),
        inspect.Parameter("arguments", inspect.Parameter.KEYWORD_ONLY, default=None, annotation=dict),
    ])
    mcp.add_tool(_gateway, name=proxy_name, description=description)
    client.set_registered_proxy_names([proxy_name])
    logger.info("Registered plugin gateway (lazy): %s", proxy_name)
    return 1


def unregister_plugin_tools(
    mcp: FastMCP,
    plugin_key: str,
    tool_names: list[str],
) -> None:
    """Remove proxy tools for a plugin from the FastMCP instance."""
    for name in tool_names:
        proxy_name = f"{plugin_key}__{name}"
        if proxy_name in mcp._tool_manager._tools:
            del mcp._tool_manager._tools[proxy_name]
            logger.info("Unregistered proxy tool: %s", proxy_name)
