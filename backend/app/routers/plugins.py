from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.mcp.plugin_config import load_plugins, save_plugins, PluginConfig, PluginsFile, PluginTransport, AccessLevel
from app.mcp.plugin_manager import plugin_manager
from app.mcp.server import mcp
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/plugins", tags=["plugins"])


def _get_project_path(project_id: str, db: AsyncSession) -> str:
    """Helper — in practice called inside routes with Depends."""
    raise NotImplementedError("use inline pattern")


@router.get("")
async def list_plugins(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    statuses = plugin_manager.get_status(project_id)
    config = load_plugins(project.path)
    result = []
    for key, cfg in config.plugins.items():
        running = next((s for s in statuses if s["name"] == key), None)
        result.append({
            "key": key,
            "name": cfg.name or key,
            "enabled": cfg.enabled,
            "transport": cfg.transport.value,
            "access_level": cfg.access_level.value,
            "connected": running["connected"] if running else False,
            "tool_count": running["tool_count"] if running else 0,
        })
    return result


@router.get("/{plugin_key}")
async def get_plugin(project_id: str, plugin_key: str, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    cfg = load_plugins(project.path).plugins.get(plugin_key)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {
        "key": plugin_key,
        "name": cfg.name or plugin_key,
        "enabled": cfg.enabled,
        "transport": cfg.transport.value,
        "command": cfg.command,
        "args": cfg.args,
        "url": cfg.url,
        "env_keys": list(cfg.env.keys()),
        "access_level": cfg.access_level.value,
        "timeout": cfg.timeout,
    }


@router.put("/{plugin_key}")
async def upsert_plugin(project_id: str, plugin_key: str, data: dict, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    plugins_file = load_plugins(project.path)

    existing = plugins_file.plugins.get(plugin_key)
    transport = data.get("transport", existing.transport.value if existing else "stdio")
    access_level = data.get("access_level", existing.access_level.value if existing else "read_only")

    cfg = PluginConfig(
        name=data.get("name", plugin_key),
        enabled=data.get("enabled", True),
        transport=PluginTransport(transport),
        command=data.get("command", ""),
        args=data.get("args", []),
        url=data.get("url", ""),
        env=data.get("env", {}),
        access_level=AccessLevel(access_level),
        timeout=data.get("timeout", 30),
    )
    plugins_file.plugins[plugin_key] = cfg
    save_plugins(project.path, plugins_file)
    return {"key": plugin_key, "name": cfg.name, "enabled": cfg.enabled}


@router.delete("/{plugin_key}")
async def delete_plugin(project_id: str, plugin_key: str, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    plugins_file = load_plugins(project.path)
    if plugin_key not in plugins_file.plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    # Disconnect if running
    await plugin_manager.disable_plugin(project_id, project.path, plugin_key, mcp)
    del plugins_file.plugins[plugin_key]
    save_plugins(project.path, plugins_file)
    return {"deleted": True}


@router.post("/{plugin_key}/enable")
async def enable_plugin(project_id: str, plugin_key: str, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    success = await plugin_manager.enable_plugin(project_id, project.path, plugin_key, mcp)
    return {"success": success}


@router.post("/{plugin_key}/disable")
async def disable_plugin(project_id: str, plugin_key: str, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    success = await plugin_manager.disable_plugin(project_id, project.path, plugin_key, mcp)
    return {"success": success}
