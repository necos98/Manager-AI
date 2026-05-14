from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from app.mcp.catalog import CatalogLoader, CatalogPlugin, OptionDef, PLUGINS_DIR
from app.mcp.plugin_config import PluginTransport, AccessLevel


class TestCatalogPlugin:
    def test_valid_stdio(self):
        cat = CatalogPlugin(
            key="test",
            name="Test",
            transport=PluginTransport.stdio,
            command="echo",
        )
        assert cat.key == "test"
        assert cat.transport == PluginTransport.stdio
        assert cat.command == "echo"

    def test_valid_http(self):
        cat = CatalogPlugin(
            key="web",
            name="Web",
            transport=PluginTransport.http,
            url="https://example.com/sse",
        )
        assert cat.transport == PluginTransport.http
        assert cat.url == "https://example.com/sse"

    def test_stdio_requires_command(self):
        with pytest.raises(ValueError, match="stdio transport requires 'command'"):
            CatalogPlugin(key="bad", name="Bad", transport=PluginTransport.stdio, command="")

    def test_http_requires_url(self):
        with pytest.raises(ValueError, match="http transport requires 'url'"):
            CatalogPlugin(key="bad", name="Bad", transport=PluginTransport.http, url="")

    def test_defaults(self):
        cat = CatalogPlugin(key="def", name="Defaults", transport=PluginTransport.stdio, command="x")
        assert cat.description == ""
        assert cat.args == []
        assert cat.url == ""
        assert cat.access_level == AccessLevel.read_only
        assert cat.timeout == 30
        assert cat.options == []


class TestOptionDef:
    def test_defaults(self):
        opt = OptionDef(key="HOST", label="Host")
        assert opt.key == "HOST"
        assert opt.label == "Host"
        assert opt.type == "string"
        assert opt.required is False
        assert opt.default == ""
        assert opt.placeholder == ""
        assert opt.choices == []

    def test_with_choices(self):
        opt = OptionDef(
            key="LEVEL",
            label="Log Level",
            type="select",
            choices=[{"value": "info", "label": "Info"}, {"value": "debug", "label": "Debug"}],
        )
        assert len(opt.choices) == 2
        assert opt.choices[0].value == "info"


class TestCatalogLoader:
    def test_load_empty_dir(self):
        loader = CatalogLoader()
        with tempfile.TemporaryDirectory() as td:
            # Override PLUGINS_DIR temporarily
            original = CatalogLoader.__module__
            loader._plugins.clear()
            # Point to empty temp dir
            loader._load_from_path(Path(td))
            assert loader._plugins == {}

    def test_load_valid_plugin(self, tmp_path):
        plugin_dir = tmp_path / "mysql"
        plugin_dir.mkdir()
        manifest = {
            "name": "MySQL",
            "description": "MySQL database plugin",
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp-server-mysql"],
            "access_level": "read_only",
            "options": [
                {"key": "MYSQL_HOST", "label": "Host", "type": "string", "required": True},
                {"key": "MYSQL_PORT", "label": "Port", "type": "string", "default": "3306"},
            ],
        }
        (plugin_dir / "plugin.yaml").write_text(yaml.dump(manifest), encoding="utf-8")

        loader = CatalogLoader()
        loader._load_from_path(tmp_path)

        assert "mysql" in loader._plugins
        cat = loader._plugins["mysql"]
        assert cat.name == "MySQL"
        assert cat.description == "MySQL database plugin"
        assert cat.transport == PluginTransport.stdio
        assert cat.command == "uvx"
        assert cat.args == ["mcp-server-mysql"]
        assert cat.access_level == AccessLevel.read_only
        assert len(cat.options) == 2
        assert cat.options[0].key == "MYSQL_HOST"
        assert cat.options[0].required is True

    def test_load_skips_invalid_manifest(self, tmp_path):
        plugin_dir = tmp_path / "bad"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text("invalid: [yaml: broken", encoding="utf-8")

        loader = CatalogLoader()
        loader._load_from_path(tmp_path)
        assert "bad" not in loader._plugins

    def test_load_skips_missing_yaml(self, tmp_path):
        plugin_dir = tmp_path / "no_yaml"
        plugin_dir.mkdir()

        loader = CatalogLoader()
        loader._load_from_path(tmp_path)
        assert "no_yaml" not in loader._plugins

    def test_build_runtime_config(self, tmp_path):
        plugin_dir = tmp_path / "mysql"
        plugin_dir.mkdir()
        manifest = {
            "name": "MySQL",
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp-server-mysql"],
            "access_level": "read_only",
        }
        (plugin_dir / "plugin.yaml").write_text(yaml.dump(manifest), encoding="utf-8")

        loader = CatalogLoader()
        loader._load_from_path(tmp_path)

        runtime = loader.build_runtime_config("mysql", True, {"MYSQL_HOST": "localhost"})
        assert runtime is not None
        assert runtime.name == "MySQL"
        assert runtime.enabled is True
        assert runtime.transport == PluginTransport.stdio
        assert runtime.command == "uvx"
        assert runtime.args == ["mcp-server-mysql"]
        assert runtime.env == {"MYSQL_HOST": "localhost"}
        assert runtime.access_level == AccessLevel.read_only
        assert runtime.timeout == 30

    def test_build_runtime_config_missing_key(self):
        loader = CatalogLoader()
        assert loader.build_runtime_config("nonexistent", True, {}) is None

    def test_get_returns_none_for_unknown(self):
        loader = CatalogLoader()
        assert loader.get("nope") is None

    def test_plugins_property_returns_copy(self, tmp_path):
        plugin_dir = tmp_path / "test"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text(yaml.dump({
            "name": "Test", "transport": "stdio", "command": "echo",
        }), encoding="utf-8")

        loader = CatalogLoader()
        loader._load_from_path(tmp_path)

        plugins = loader.plugins
        plugins["new"] = CatalogPlugin(key="new", name="New", transport=PluginTransport.stdio, command="x")
        assert "new" not in loader._plugins  # returned a copy


# Patch CatalogLoader to support loading from arbitrary path
def _load_from_path(self, path: Path) -> None:
    self._plugins.clear()
    if not path.is_dir():
        return
    for plugin_dir in sorted(path.iterdir()):
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / "plugin.yaml"
        if not manifest_path.exists():
            continue
        try:
            raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            raw["key"] = plugin_dir.name
            plugin = CatalogPlugin(**raw)
            self._plugins[plugin.key] = plugin
        except Exception:
            pass


CatalogLoader._load_from_path = _load_from_path
