from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.project_setting_service import ProjectSettingService

_MCP_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "mcp" / "default_settings.json"
_TOOL_DESC_PREFIX = "mcp_tool_desc."


class McpToolDescriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._defaults: dict[str, str] = self._load_defaults()

    def _load_defaults(self) -> dict[str, str]:
        if not _MCP_SETTINGS_PATH.exists():
            return {}
        data = json.loads(_MCP_SETTINGS_PATH.read_text(encoding="utf-8"))
        return {
            k.removeprefix("tool.").removesuffix(".description"): v
            for k, v in data.items()
            if k.startswith("tool.") and k.endswith(".description")
        }

    async def get_project_overrides(self, project_id: str) -> dict[str, str]:
        """Return {tool_name: custom_description} for all overrides on this project."""
        svc = ProjectSettingService(self.session)
        all_settings = await svc.get_all_for_project(project_id)
        return {
            k.removeprefix(_TOOL_DESC_PREFIX): v
            for k, v in all_settings.items()
            if k.startswith(_TOOL_DESC_PREFIX)
        }

    async def build_tool_guidance(self, project_id: str) -> str:
        """Build a [Tool guidance] block to inject into prompts, if any overrides exist."""
        overrides = await self.get_project_overrides(project_id)
        if not overrides:
            return ""
        lines = ["[Tool guidance for this project]"]
        for tool, desc in overrides.items():
            lines.append(f"{tool}: {desc}")
        return "\n".join(lines)
