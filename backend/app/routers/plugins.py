from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.mcp.plugin_config import load_plugins, save_plugins, set_plugin_config, PluginsFile
from app.mcp.plugin_manager import plugin_manager
from app.mcp.catalog import catalog_loader
from app.mcp.server import mcp
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/plugins", tags=["plugins"])
catalog_router = APIRouter(prefix="/api/plugins", tags=["plugins"])


# ── Catalog endpoints (no project_id) ────────────────────────────────────────


@catalog_router.get("/catalog")
async def get_catalog():
    """List all available plugins in the built-in catalog."""
    return [
        {
            "key": p.key,
            "name": p.name,
            "description": p.description,
            "transport": p.transport.value,
            "access_level": p.access_level.value,
            "options": [
                {
                    "key": o.key,
                    "label": o.label,
                    "type": o.type,
                    "required": o.required,
                    "default": o.default,
                    "placeholder": o.placeholder,
                    "choices": [{"value": c.value, "label": c.label} for c in o.choices],
                }
                for o in p.options
            ],
        }
        for p in catalog_loader.plugins.values()
    ]


# ── Project plugin endpoints ────────────────────────────────────────────────


@router.get("")
async def list_plugins(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    statuses = plugin_manager.get_status(project_id)
    config = load_plugins(project.path)

    result = []
    seen: set[str] = set()

    # Catalog plugins (enabled or not)
    for key, cat in catalog_loader.plugins.items():
        proj_cfg = config.plugins.get(key)
        running = next((s for s in statuses if s["name"] == key), None)
        result.append({
            "key": key,
            "name": cat.name,
            "description": cat.description,
            "enabled": proj_cfg.enabled if proj_cfg else False,
            "transport": cat.transport.value,
            "access_level": cat.access_level.value,
            "connected": running["connected"] if running else False,
            "tool_count": running["tool_count"] if running else 0,
            "configured": proj_cfg is not None,
            "config": proj_cfg.config if proj_cfg else {},
            "catalog": True,
        })
        seen.add(key)

    # Legacy plugins (from v1, not in catalog)
    for key, proj_cfg in config.plugins.items():
        if key not in seen:
            running = next((s for s in statuses if s["name"] == key), None)
            result.append({
                "key": key,
                "name": key,
                "description": "Legacy plugin (no catalog entry)",
                "enabled": proj_cfg.enabled,
                "transport": "unknown",
                "access_level": "unknown",
                "connected": running["connected"] if running else False,
                "tool_count": running["tool_count"] if running else 0,
                "configured": True,
                "config": proj_cfg.config,
                "catalog": False,
                "legacy": True,
            })

    return result


@router.get("/{plugin_key}")
async def get_plugin(project_id: str, plugin_key: str, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    proj_cfg = load_plugins(project.path).plugins.get(plugin_key)
    if proj_cfg is None:
        raise HTTPException(status_code=404, detail="Plugin not found")

    cat = catalog_loader.get(plugin_key)
    name = cat.name if cat else plugin_key
    description = cat.description if cat else "Legacy plugin (no catalog entry)"
    transport = cat.transport.value if cat else "unknown"
    access_level = cat.access_level.value if cat else "unknown"

    return {
        "key": plugin_key,
        "name": name,
        "description": description,
        "enabled": proj_cfg.enabled,
        "transport": transport,
        "access_level": access_level,
        "config": proj_cfg.config,
        "catalog": cat is not None,
    }


@router.put("/{plugin_key}")
async def upsert_plugin(project_id: str, plugin_key: str, data: dict, db: AsyncSession = Depends(get_db)):
    cat = catalog_loader.get(plugin_key)
    if cat is None:
        raise HTTPException(status_code=400, detail=f"Plugin '{plugin_key}' not found in catalog")

    project = await ProjectService(db).get_by_id(project_id)
    enabled = data.get("enabled", True)
    config = data.get("config", {})

    set_plugin_config(project.path, plugin_key, enabled, config)

    if enabled:
        await plugin_manager.enable_plugin(project_id, project.path, plugin_key, mcp, config)
    else:
        await plugin_manager.disable_plugin(project_id, project.path, plugin_key, mcp)

    return {"key": plugin_key, "name": cat.name, "enabled": enabled, "config": config}


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
