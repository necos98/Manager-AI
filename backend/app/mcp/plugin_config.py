from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.storage import atomic


class PluginTransport(str, Enum):
    stdio = "stdio"
    http = "http"


class AccessLevel(str, Enum):
    read_only = "read_only"
    read_write = "read_write"
    admin = "admin"


class PluginConfig(BaseModel):
    name: str = ""
    enabled: bool = True
    transport: PluginTransport = PluginTransport.stdio
    command: str = ""
    args: list[str] = Field(default_factory=list)
    url: str = ""
    env: dict[str, str] = Field(default_factory=dict)
    access_level: AccessLevel = AccessLevel.read_only
    timeout: int = 30
    connect_timeout: int = 20

    @model_validator(mode="after")
    def _validate_transport_fields(self) -> "PluginConfig":
        if self.transport == PluginTransport.stdio:
            if not self.command:
                raise ValueError("stdio transport requires 'command'")
        elif self.transport == PluginTransport.http:
            if not self.url:
                raise ValueError("http transport requires 'url'")
        return self

    def to_description_tag(self) -> str:
        """Short tag injected into tool descriptions."""
        return f"[{self.name} plugin — {self.access_level.value}]"

    def tool_prefix(self, plugin_key: str) -> str:
        return f"{plugin_key}__"


class ProjectPluginConfig(BaseModel):
    """Per-project plugin instance config (v2). References catalog by key."""
    enabled: bool = False
    config: dict[str, str] = Field(default_factory=dict)


class PluginsFile(BaseModel):
    schema_version: int = 2
    plugins: dict[str, ProjectPluginConfig] = Field(default_factory=dict)


def _plugins_yaml_path(project_path: str) -> Path:
    return Path(project_path) / ".manager_ai" / "plugins.yaml"


def load_plugins(project_path: str) -> PluginsFile:
    path = _plugins_yaml_path(project_path)
    raw = atomic.read_yaml(path) or {}
    if not raw:
        return PluginsFile()
    version = raw.get("schema_version", 1)
    plugins_raw = raw.get("plugins", {}) or {}
    plugins: dict[str, ProjectPluginConfig] = {}
    for key, cfg in plugins_raw.items():
        try:
            if version >= 2:
                plugins[key] = ProjectPluginConfig(**cfg)
            else:
                # V1: PluginConfig has enabled + env fields, migrate to v2 format
                v1 = PluginConfig(**cfg)
                plugins[key] = ProjectPluginConfig(
                    enabled=v1.enabled,
                    config=v1.env,
                )
        except Exception:
            pass
    return PluginsFile(plugins=plugins, schema_version=2)


def save_plugins(project_path: str, plugins_file: PluginsFile) -> None:
    path = _plugins_yaml_path(project_path)
    data: dict[str, Any] = {
        "schema_version": plugins_file.schema_version,
        "plugins": {
            key: cfg.model_dump(mode="json")
            for key, cfg in plugins_file.plugins.items()
        },
    }
    atomic.write_yaml(path, data)


def get_plugin_config(project_path: str, plugin_name: str) -> ProjectPluginConfig | None:
    pf = load_plugins(project_path)
    return pf.plugins.get(plugin_name)


def set_plugin_enabled(project_path: str, plugin_name: str, enabled: bool) -> bool:
    pf = load_plugins(project_path)
    cfg = pf.plugins.get(plugin_name)
    if cfg is None:
        return False
    cfg.enabled = enabled
    save_plugins(project_path, pf)
    return True


def set_plugin_config(project_path: str, plugin_name: str, enabled: bool, config: dict[str, str]) -> bool:
    pf = load_plugins(project_path)
    cfg = pf.plugins.get(plugin_name)
    if cfg is None:
        pf.plugins[plugin_name] = ProjectPluginConfig(enabled=enabled, config=config)
    else:
        cfg.enabled = enabled
        cfg.config = config
    save_plugins(project_path, pf)
    return True
