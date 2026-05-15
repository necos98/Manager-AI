from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from app.mcp.plugin_config import PluginTransport, AccessLevel

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).resolve().parent.parent.parent / "plugins"


class OptionChoice(BaseModel):
    value: str
    label: str


class OptionDef(BaseModel):
    key: str
    label: str
    type: Literal["string", "secret", "number", "boolean", "select"] = "string"
    required: bool = False
    default: str = ""
    placeholder: str = ""
    choices: list[OptionChoice] = Field(default_factory=list)


class CatalogPlugin(BaseModel):
    key: str  # set from directory name, not in YAML
    name: str
    description: str = ""
    transport: PluginTransport = PluginTransport.stdio
    command: str = ""
    args: list[str] = Field(default_factory=list)
    url: str = ""
    access_level: AccessLevel = AccessLevel.read_only
    timeout: int = 30
    connect_timeout: int = 20
    options: list[OptionDef] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_transport(self) -> "CatalogPlugin":
        if self.transport == PluginTransport.stdio and not self.command:
            raise ValueError("stdio transport requires 'command'")
        if self.transport == PluginTransport.http and not self.url:
            raise ValueError("http transport requires 'url'")
        return self


class CatalogLoader:
    def __init__(self) -> None:
        self._plugins: dict[str, CatalogPlugin] = {}
        self._loaded = False

    @property
    def plugins(self) -> dict[str, CatalogPlugin]:
        return dict(self._plugins)

    def get(self, key: str) -> CatalogPlugin | None:
        return self._plugins.get(key)

    def load(self) -> None:
        self._plugins.clear()
        if not PLUGINS_DIR.is_dir():
            logger.warning("Plugins directory not found: %s", PLUGINS_DIR)
            self._loaded = True
            return
        for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
            if not plugin_dir.is_dir():
                continue
            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                logger.warning("No plugin.yaml in %s, skipping", plugin_dir)
                continue
            try:
                raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                raw["key"] = plugin_dir.name
                plugin = CatalogPlugin(**raw)
                self._plugins[plugin.key] = plugin
                logger.info("Loaded catalog plugin: %s", plugin.key)
            except Exception as exc:
                logger.warning("Failed to load plugin %s: %s", plugin_dir.name, exc)
        self._loaded = True

    def build_runtime_config(
        self, catalog_key: str, enabled: bool, user_config: dict[str, str]
    ) -> "PluginConfig | None":
        from app.mcp.plugin_config import PluginConfig

        cat = self.get(catalog_key)
        if cat is None:
            return None
        return PluginConfig(
            name=cat.name,
            enabled=enabled,
            transport=cat.transport,
            command=cat.command,
            args=cat.args,
            url=cat.url,
            env=user_config,
            access_level=cat.access_level,
            timeout=cat.timeout,
            connect_timeout=cat.connect_timeout,
        )


catalog_loader = CatalogLoader()
