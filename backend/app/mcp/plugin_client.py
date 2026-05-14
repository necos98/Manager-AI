from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.types import Tool

logger = logging.getLogger(__name__)


def _extract_error_message(exc: BaseException) -> str:
    """Unwrap ExceptionGroup and extract the most useful error message."""
    msg = str(exc)

    # Unwrap ExceptionGroup to find the innermost meaningful message
    current = exc
    while isinstance(current, BaseExceptionGroup) and current.exceptions:
        current = current.exceptions[0]
    inner_msg = str(current)

    # If the outer message is generic but inner has more detail, use inner
    if msg.startswith("unhandled errors in a TaskGroup") and inner_msg != msg:
        return inner_msg
    return msg


def _is_anyio_closed_error(exc: BaseException) -> bool:
    """Check whether an exception (or ExceptionGroup) stems from a closed resource."""
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_anyio_closed_error(e) for e in exc.exceptions)
    module = getattr(type(exc), "__module__", "")
    name = type(exc).__name__
    return module.startswith("anyio") and "Closed" in name


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
    _tool_schemas: list[dict] = field(default_factory=list, repr=False, init=False)
    _registered_proxy_names: list[str] = field(default_factory=list, repr=False, init=False)
    _read_stream: Any = field(default=None, repr=False, init=False)
    _write_stream: Any = field(default=None, repr=False, init=False)
    _transport_ctx: Any = field(default=None, repr=False, init=False)
    _connected: bool = field(default=False, repr=False, init=False)
    _stderr_file: Any = field(default=None, repr=False, init=False)
    _stderr_path: str | None = field(default=None, repr=False, init=False)
    _connect_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False, init=False)

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def tools(self) -> list[Tool]:
        return list(self._tools)

    @property
    def tool_schemas(self) -> list[dict]:
        return list(self._tool_schemas)

    @property
    def tool_names(self) -> list[str]:
        """Proxy tool names registered on FastMCP for this plugin."""
        if self._registered_proxy_names:
            return list(self._registered_proxy_names)
        if self._tool_schemas:
            return [s["name"] for s in self._tool_schemas]
        return [t.name for t in self._tools]

    def set_registered_proxy_names(self, names: list[str]) -> None:
        self._registered_proxy_names = names

    async def ensure_connected(self) -> None:
        """Connect if not already connected. Locked — safe under concurrent calls."""
        if self._connected:
            return
        async with self._connect_lock:
            if self._connected:
                return
            await self.connect()

    async def discover_and_disconnect(self) -> list[dict]:
        """Connect, discover tools, store schemas, then disconnect.

        Returns the list of tool schemas discovered.
        """
        async with self._connect_lock:
            await self.connect()
            schemas = [
                {"name": t.name, "inputSchema": getattr(t, "inputSchema", {}) or {}}
                for t in self._tools
            ]
            self._tool_schemas = schemas
            await self.disconnect()
        return schemas

    async def connect(self) -> None:
        if self._connected:
            return
        try:
            if self.transport == "stdio":
                await self._connect_stdio()
            elif self.transport == "http":
                await self._connect_http()
            else:
                raise ValueError(f"Unsupported transport: {self.transport}")
        except BaseException:
            logger.exception("Plugin %s connect failed", self.plugin_name)
            await self._cleanup_on_connect_failure()
            raise

    async def _connect_stdio(self) -> None:
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env if self.env else None,
        )
        self._stderr_file = tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".stderr", encoding="utf-8"
        )
        self._stderr_path = self._stderr_file.name
        self._transport_ctx = stdio_client(server_params, errlog=self._stderr_file)
        try:
            read_stream, write_stream = await self._transport_ctx.__aenter__()
        except BaseException:
            logger.exception("Plugin %s __aenter__ failed", self.plugin_name)
            self._transport_ctx = None
            self._cleanup_stderr_file()
            raise
        self._read_stream = read_stream
        self._write_stream = write_stream
        try:
            await self._init_session(read_stream, write_stream)
        except BaseException as exc:
            stderr_output = self._read_stderr()
            logger.warning(
                "Plugin %s _init_session failed | type=%s str=[%s] stderr_len=%d",
                self.plugin_name, type(exc).__name__, str(exc), len(stderr_output),
            )
            # Exit the transport context to kill the subprocess — it's in a
            # failed state and we don't want zombie processes.
            await self._exit_transport()
            self._cleanup_stderr_file()
            if stderr_output:
                raise RuntimeError(
                    f"Plugin process exited with error:\n{stderr_output}"
                ) from None
            raise

    def _read_stderr(self) -> str:
        if not self._stderr_file:
            return ""
        try:
            self._stderr_file.flush()
            self._stderr_file.seek(0)
            return self._stderr_file.read().strip()
        except Exception:
            return ""

    def _cleanup_stderr_file(self) -> None:
        if self._stderr_file:
            try:
                self._stderr_file.close()
            except Exception:
                pass
            self._stderr_file = None
        if self._stderr_path:
            try:
                os.unlink(self._stderr_path)
            except OSError:
                pass
            self._stderr_path = None

    async def _connect_http(self) -> None:
        self._transport_ctx = sse_client(self.url, timeout=self.timeout)
        try:
            read_stream, write_stream = await self._transport_ctx.__aenter__()
        except BaseException:
            logger.exception("Plugin %s SSE __aenter__ failed", self.plugin_name)
            self._transport_ctx = None
            raise
        self._read_stream = read_stream
        self._write_stream = write_stream
        try:
            await self._init_session(read_stream, write_stream)
        except BaseException:
            logger.exception("Plugin %s SSE _init_session failed", self.plugin_name)
            await self._exit_transport()
            raise

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

    async def _exit_transport(self) -> None:
        """Exit the transport context manager without marking disconnected.

        Used when the connection is in a failed state and we need to kill
        the subprocess without going through the full disconnect path.
        """
        if self._session:
            try:
                await asyncio.wait_for(self._session.__aexit__(None, None, None), timeout=3)
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

    async def _cleanup_on_connect_failure(self) -> None:
        """Clean up state after a failed connect() attempt."""
        self._connected = False
        await self._exit_transport()
        self._cleanup_stderr_file()

    async def disconnect(self) -> None:
        self._connected = False
        await self._exit_transport()
        self._cleanup_stderr_file()
        self._tools.clear()
        # _tool_schemas preserved for re-registration on reconnect

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
        except BaseException as exc:
            # Catch ExceptionGroup and anyio closed-resource errors that can
            # propagate when the subprocess dies mid-call.  BaseException is
            # broad on purpose — ExceptionGroup extends BaseException, not
            # Exception, so a plain 'except Exception' misses it.
            if _is_anyio_closed_error(exc):
                self._connected = False
                return {"error": f"Plugin {self.plugin_name} connection lost: subprocess exited"}
            logger.warning(
                "Plugin %s call_tool(%s) unexpected error: %s",
                self.plugin_name, tool_name, exc,
            )
            return {"error": f"Plugin {self.plugin_name} error: {exc}"}
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
