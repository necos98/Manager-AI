from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from app.mcp.plugin_client import PluginClient
from app.mcp.plugin_config import (
    AccessLevel,
    PluginConfig,
    load_plugins,
    set_plugin_enabled,
)
from app.mcp.plugin_proxy import register_plugin_tools, unregister_plugin_tools
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
                "tool_count": len(ps.client.tools),
                "tool_names": [t.name for t in ps.client.tools],
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

        for key, cfg in plugins_file.plugins.items():
            if not cfg.enabled:
                continue
            if key in existing:
                logger.warning("Plugin %s already running for project %s, skipping", key, project_id)
                continue
            await self._start_one(project_id, project_path, key, cfg, mcp_instance)

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

        try:
            await client.connect()
        except Exception as exc:
            logger.error("Plugin %s (project %s) failed to connect: %s", key, project_id, exc)
            await self._emit_plugin_event(project_id, key, "plugin_failed", str(exc))
            return

        try:
            registered = register_plugin_tools(
                mcp_instance, key, client, cfg.access_level
            )
        except Exception as exc:
            logger.error("Plugin %s (project %s) tool registration failed: %s", key, project_id, exc)
            await self._emit_plugin_event(project_id, key, "plugin_failed", str(exc))
            await client.disconnect()
            return

        await self._emit_plugin_event(project_id, key, "plugin_started", f"{registered} tools registered")

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

        # Unregister old tools
        try:
            unregister_plugin_tools(mcp_instance, plugin_key, state.client.tools)
        except Exception:
            pass

        # Reconnect with fresh client
        cfg = state.config
        new_client = PluginClient(
            plugin_name=cfg.name or plugin_key,
            transport=cfg.transport.value,
            command=cfg.command,
            args=cfg.args,
            url=cfg.url,
            env=cfg.env,
            timeout=cfg.timeout,
        )
        state.client = new_client

        try:
            await new_client.connect()
            register_plugin_tools(mcp_instance, plugin_key, new_client, cfg.access_level)
            await self._emit_plugin_event(project_id, plugin_key, "plugin_started", "Restarted")
            return True
        except Exception as exc:
            logger.error("Plugin %s restart failed: %s", plugin_key, exc)
            await self._emit_plugin_event(project_id, plugin_key, "plugin_failed", str(exc))
            return False

    async def enable_plugin(
        self,
        project_id: str,
        project_path: str,
        plugin_key: str,
        mcp_instance: FastMCP,
    ) -> bool:
        if not set_plugin_enabled(project_path, plugin_key, True):
            return False
        cfg_file = load_plugins(project_path)
        cfg = cfg_file.plugins.get(plugin_key)
        if cfg is None:
            return False
        await self._start_one(project_id, project_path, plugin_key, cfg, mcp_instance)
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
