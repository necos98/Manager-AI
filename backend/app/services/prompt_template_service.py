from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.prompt_template import PromptTemplate
from app.schemas.prompt_template import TemplateInfo


def _parse_template_file(path: Path) -> str:
    """Read template file, strip YAML frontmatter, return body."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    return parts[2].lstrip("\n") if len(parts) >= 3 else content


TEMPLATE_TYPES = ["spec", "plan", "recap", "enrich", "workflow", "implementation"]


class PromptTemplateService:
    def __init__(self, session: AsyncSession, library_path: str | None = None):
        self.session = session
        self._library = Path(library_path or settings.claude_library_path)

    async def resolve(
        self, type: str, project_id: str, variables: dict[str, str]
    ) -> str:
        """Resolve template with variable substitution.

        Priority: DB override → file default → empty string fallback.
        """
        content = await self._get_raw(type, project_id)
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content

    async def get_template_info(self, type: str, project_id: str) -> TemplateInfo:
        row = await self._get_db_override(type, project_id)
        if row:
            return TemplateInfo(type=type, content=row.content, is_overridden=True)
        file_content = self._read_file(type)
        return TemplateInfo(type=type, content=file_content, is_overridden=False)

    async def list_for_project(self, project_id: str) -> list[TemplateInfo]:
        return [
            await self.get_template_info(t, project_id) for t in TEMPLATE_TYPES
        ]

    async def save_override(self, type: str, project_id: str, content: str) -> None:
        row = await self._get_db_override(type, project_id)
        if row:
            row.content = content
        else:
            self.session.add(
                PromptTemplate(project_id=project_id, type=type, content=content)
            )
        await self.session.flush()

    async def delete_override(self, type: str, project_id: str) -> None:
        row = await self._get_db_override(type, project_id)
        if row:
            await self.session.delete(row)
            await self.session.flush()

    # ── private ──────────────────────────────────────────────────────────────

    async def _get_raw(self, type: str, project_id: str) -> str:
        row = await self._get_db_override(type, project_id)
        if row:
            return row.content
        return self._read_file(type)

    async def _get_db_override(self, type: str, project_id: str) -> PromptTemplate | None:
        result = await self.session.execute(
            select(PromptTemplate).where(
                PromptTemplate.project_id == project_id,
                PromptTemplate.type == type,
            )
        )
        return result.scalar_one_or_none()

    def _read_file(self, type: str) -> str:
        path = self._library / "templates" / f"{type}.md"
        if not path.exists():
            return ""
        return _parse_template_file(path)
