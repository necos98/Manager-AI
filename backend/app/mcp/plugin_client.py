from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.types import Tool

logger = logging.getLogger(__name__)


@dataclass
class PluginClient:
    plugin_name: str
    transport: str  # "stdio" | "http"
    command: str = ""
    args: list[str] = field(default_factory=list)
    url: str = ""
    env: dict[str, str] = field(default_factory=dict)
    timeout: int = 30

    _session: ClientSession | None = field(default=None, repr=False, init=False)
    _tools: list[Tool] = field(default_factory=list, repr=False, init=False)
    _read_stream: Any = field(default=None, repr=False, init=False)
    _write_stream: Any = field(default=None, repr=False, init=False)
    _transport_ctx: Any = field(default=None, repr=False, init=False)
    _connected: bool = field(default=False, repr=False, init=False)

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def tools(self) -> list[Tool]:
        return list(self._tools)

    async def connect(self) -> None:
        if self.transport == "stdio":
            await self._connect_stdio()
        elif self.transport == "http":
            await self._connect_http()
        else:
            raise ValueError(f"Unsupported transport: {self.transport}")

    async def _connect_stdio(self) -> None:
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env if self.env else None,
        )
        self._transport_ctx = stdio_client(server_params)
        read_stream, write_stream = await self._transport_ctx.__aenter__()
        self._read_stream = read_stream
        self._write_stream = write_stream
        await self._init_session(read_stream, write_stream)

    async def _connect_http(self) -> None:
        self._transport_ctx = sse_client(self.url, timeout=self.timeout)
        read_stream, write_stream = await self._transport_ctx.__aenter__()
        self._read_stream = read_stream
        self._write_stream = write_stream
        await self._init_session(read_stream, write_stream)

    async def _init_session(self, read_stream: Any, write_stream: Any) -> None:
        self._session = ClientSession(read_stream, write_stream)
        await self._session.__aenter__()
        await self._session.initialize()
        result = await self._session.list_tools()
        self._tools = list(result.tools) if result.tools else []
        self._connected = True
        logger.info(
            "Plugin %s connected with %d tools: %s",
            self.plugin_name,
            len(self._tools),
            [t.name for t in self._tools],
        )

    async def disconnect(self) -> None:
        self._connected = False
        if self._session:
            try:
                await asyncio.wait_for(self._session.__aexit__(None, None, None), timeout=5)
            except (asyncio.TimeoutError, Exception):
                pass
            self._session = None
        if self._transport_ctx:
            try:
                await asyncio.wait_for(self._transport_ctx.__aexit__(None, None, None), timeout=5)
            except (asyncio.TimeoutError, Exception):
                pass
            self._transport_ctx = None
        self._read_stream = None
        self._write_stream = None
        self._tools.clear()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict:
        if not self._session or not self._connected:
            raise RuntimeError(f"Plugin {self.plugin_name} not connected")
        try:
            result = await asyncio.wait_for(
                self._session.call_tool(tool_name, arguments or {}),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            return {"error": f"Plugin {self.plugin_name} tool {tool_name} timed out after {self.timeout}s"}
        return _call_tool_result_to_dict(result)


def _call_tool_result_to_dict(result: Any) -> dict:
    """Convert an MCP CallToolResult into a plain dict for proxying."""
    try:
        content = getattr(result, "content", None) or []
        text_parts = []
        for item in content:
            item_type = getattr(item, "type", "text")
            if item_type == "text":
                text_parts.append(getattr(item, "text", str(item)))
            elif item_type == "resource":
                text_parts.append(f"[resource: {getattr(item, 'resource', item)}]")
            else:
                text_parts.append(str(item))
        meta = getattr(result, "meta", None)
        is_error = getattr(result, "isError", False)
        out: dict[str, Any] = {"content": "\n".join(text_parts) if text_parts else str(result), "is_error": is_error}
        if meta:
            out["meta"] = meta
        return out
    except Exception:
        return {"content": str(result), "is_error": False}
