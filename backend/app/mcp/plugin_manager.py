from __future__ import annotations

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from app.mcp.plugin_client import PluginClient, _extract_error_message
from app.mcp.plugin_config import (
    AccessLevel,
    PluginConfig,
    load_plugins,
    set_plugin_config,
    set_plugin_enabled,
)
from app.mcp.plugin_proxy import register_plugin_gateway, register_plugin_tools, register_plugin_tools_from_schemas, unregister_plugin_tools
from app.mcp.catalog import catalog_loader
from app.services.event_service import event_service

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_WINDOW_SECONDS = 60
COOLDOWN_SECONDS = 300


@dataclass
class _PluginState:
    client: PluginClient
    config: PluginConfig
    retry_count: int = 0
    first_retry_at: float = 0.0
    cooldown_until: float = 0.0


class PluginManager:
    def __init__(self) -> None:
        # project_id -> {plugin_key: _PluginState}
        self._state: dict[str, dict[str, _PluginState]] = {}

    def get_status(self, project_id: str) -> list[dict]:
        entries = self._state.get(project_id, {})
        result = []
        for key, ps in entries.items():
            result.append({
                "name": key,
                "plugin_name": ps.config.name or key,
                "transport": ps.config.transport.value,
                "access_level": ps.config.access_level.value,
                "enabled": ps.config.enabled,
                "connected": ps.client.connected,
                "tool_count": len(ps.client.tool_names),
                "tool_names": ps.client.tool_names,
            })
        return result

    async def start_plugins_for_project(
        self,
        project_id: str,
        project_path: str,
        mcp_instance: FastMCP,
    ) -> None:
        plugins_file = load_plugins(project_path)
        if not plugins_file.plugins:
            return

        self._state.setdefault(project_id, {})
        existing = self._state[project_id]

        for key, proj_cfg in plugins_file.plugins.items():
            if not proj_cfg.enabled:
                continue
            if key in existing:
                logger.warning("Plugin %s already running for project %s, skipping", key, project_id)
                continue
            runtime_cfg = catalog_loader.build_runtime_config(key, True, proj_cfg.config)
            if runtime_cfg is None:
                logger.warning("Plugin %s not in catalog, skipping legacy plugin", key)
                continue
            await self._start_one(project_id, project_path, key, runtime_cfg, mcp_instance)

    async def _start_one(
        self,
        project_id: str,
        project_path: str,
        key: str,
        cfg: PluginConfig,
        mcp_instance: FastMCP,
    ) -> None:
        client = PluginClient(
            plugin_name=cfg.name or key,
            transport=cfg.transport.value,
            command=cfg.command,
            args=cfg.args,
            url=cfg.url,
            env=cfg.env,
            timeout=cfg.timeout,
        )
        state = _PluginState(client=client, config=cfg)
        self._state.setdefault(project_id, {})[key] = state

        # Register a single gateway tool per plugin — zero process spawn.
        # The real plugin process starts only on first tool call or Test Connection.
        try:
            registered = register_plugin_gateway(
                mcp_instance, key, client, cfg.access_level, (cfg.name or key)
            )
        except Exception as exc:
            error_msg = _extract_error_message(exc)
            logger.error("Plugin %s (project %s) gateway registration failed: %s\n%s", key, project_id, error_msg, traceback.format_exc())
            self._state[project_id].pop(key, None)
            await self._emit_plugin_event(project_id, key, "plugin_failed", error_msg)
            return

        # Pre-connect in background so first tool call is fast.
        # If we wait for the first call, uvx/npx setup can take 30+s and the
        # MCP client times out, drops SSE, causing ClosedResourceError on
        # subsequent requests.
        async def _pre_connect():
            try:
                await client.connect()
            except BaseException:
                logger.debug("Plugin %s background pre-connect failed (will retry on first call)", key)

        asyncio.create_task(_pre_connect())

        await self._emit_plugin_event(project_id, key, "plugin_ready", f"{registered} gateway registered (lazy connect)")

    async def stop_plugins_for_project(self, project_id: str) -> None:
        entries = self._state.pop(project_id, {})
        for key, ps in entries.items():
            try:
                await ps.client.disconnect()
            except Exception as exc:
                logger.warning("Error disconnecting plugin %s: %s", key, exc)
            await self._emit_plugin_event(project_id, key, "plugin_stopped", "")

    async def restart_plugin(
        self,
        project_id: str,
        project_path: str,
        plugin_key: str,
        mcp_instance: FastMCP,
    ) -> bool:
        entries = self._state.get(project_id, {})
        ps = entries.get(plugin_key)
        if ps is None:
            return False

        state = ps
        now = datetime.now(timezone.utc).timestamp()

        if state.cooldown_until > now:
            logger.warning("Plugin %s in cooldown until %s", plugin_key, state.cooldown_until)
            return False

        if state.first_retry_at > 0 and (now - state.first_retry_at) < RETRY_WINDOW_SECONDS:
            state.retry_count += 1
        else:
            state.retry_count = 1
            state.first_retry_at = now

        if state.retry_count > MAX_RETRIES:
            state.cooldown_until = now + COOLDOWN_SECONDS
            state.retry_count = 0
            logger.error("Plugin %s exceeded max retries, cooldown %ss", plugin_key, COOLDOWN_SECONDS)
            await self._emit_plugin_event(project_id, plugin_key, "plugin_failed", "Max retries exceeded, in cooldown")
            return False

        # Disconnect existing
        try:
            await state.client.disconnect()
        except Exception:
            pass

        # Unregister old gateway
        try:
            unregister_plugin_tools(mcp_instance, plugin_key, state.client.tool_names)
        except Exception:
            pass

        # Reconnect with fresh client — rebuild from catalog + stored config
        plugins_file = load_plugins(project_path)
        proj_cfg = plugins_file.plugins.get(plugin_key)
        user_config = proj_cfg.config if proj_cfg else {}
        runtime_cfg = catalog_loader.build_runtime_config(plugin_key, True, user_config)
        if runtime_cfg is None:
            logger.warning("Plugin %s no longer in catalog, cannot restart", plugin_key)
            return False
        state.config = runtime_cfg
        new_client = PluginClient(
            plugin_name=runtime_cfg.name or plugin_key,
            transport=runtime_cfg.transport.value,
            command=runtime_cfg.command,
            args=runtime_cfg.args,
            url=runtime_cfg.url,
            env=runtime_cfg.env,
            timeout=runtime_cfg.timeout,
        )
        state.client = new_client

        try:
            register_plugin_gateway(mcp_instance, plugin_key, new_client, runtime_cfg.access_level, runtime_cfg.name or plugin_key)

            async def _pre_connect():
                try:
                    await new_client.connect()
                except BaseException:
                    logger.debug("Plugin %s background pre-connect failed (will retry on first call)", plugin_key)

            asyncio.create_task(_pre_connect())

            await self._emit_plugin_event(project_id, plugin_key, "plugin_ready", "Restarted (lazy connect)")
            return True
        except Exception as exc:
            error_msg = _extract_error_message(exc)
            logger.error("Plugin %s restart failed: %s", plugin_key, error_msg)
            await self._emit_plugin_event(project_id, plugin_key, "plugin_failed", error_msg)
            return False

    async def enable_plugin(
        self,
        project_id: str,
        project_path: str,
        plugin_key: str,
        mcp_instance: FastMCP,
        config: dict[str, str] | None = None,
    ) -> bool:
        cat = catalog_loader.get(plugin_key)
        if cat is None:
            logger.warning("Plugin %s not found in catalog, cannot enable", plugin_key)
            return False
        user_config = config or {}
        set_plugin_config(project_path, plugin_key, True, user_config)
        runtime_cfg = catalog_loader.build_runtime_config(plugin_key, True, user_config)
        if runtime_cfg is None:
            return False
        await self._start_one(project_id, project_path, plugin_key, runtime_cfg, mcp_instance)
        return True

    async def disable_plugin(
        self,
        project_id: str,
        project_path: str,
        plugin_key: str,
        mcp_instance: FastMCP,
    ) -> bool:
        if not set_plugin_enabled(project_path, plugin_key, False):
            return False
        entries = self._state.get(project_id, {})
        ps = entries.get(plugin_key)
        if ps is None:
            return True
        try:
            unregister_plugin_tools(mcp_instance, plugin_key, ps.client.tools)
        except Exception:
            pass
        try:
            await ps.client.disconnect()
        except Exception:
            pass
        entries.pop(plugin_key, None)
        await self._emit_plugin_event(project_id, plugin_key, "plugin_stopped", "")
        return True

    async def _emit_plugin_event(self, project_id: str, plugin_key: str, event_type: str, detail: str) -> None:
        try:
            await event_service.emit({
                "type": event_type,
                "project_id": project_id,
                "plugin_key": plugin_key,
                "detail": detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass


plugin_manager = PluginManager()
