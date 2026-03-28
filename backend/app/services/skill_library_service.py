from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AppError, NotFoundError
from app.models.project_skill import ProjectSkill
from app.schemas.library import SkillCreate, SkillDetail, SkillMeta


MANAGER_AI_MARKER_BEGIN = "<!-- MANAGER AI BEGIN -->"
MANAGER_AI_MARKER_END = "<!-- MANAGER AI END -->"


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from a markdown file."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        meta = {}
    return meta, parts[2].lstrip("\n")


class SkillLibraryService:
    def __init__(self, session: AsyncSession | None):
        self.session = session
        self._library_path = Path(settings.claude_library_path)

    def _dir(self, type: str) -> Path:
        return self._library_path / ("skills" if type == "skill" else "agents")

    def list_available(self, type: str = "skill") -> list[SkillMeta]:
        """Read skill/agent files from the filesystem library."""
        directory = self._dir(type)
        if not directory.exists():
            return []
        result = []
        for path in sorted(directory.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            meta, _ = _parse_frontmatter(content)
            result.append(
                SkillMeta(
                    name=meta.get("name", path.stem),
                    category=meta.get("category", ""),
                    description=meta.get("description", ""),
                    built_in=bool(meta.get("built_in", False)),
                    type=type,
                )
            )
        return result

    def get_content(self, name: str, type: str) -> SkillDetail:
        """Return full skill detail including content."""
        path = self._dir(type) / f"{name}.md"
        if not path.exists():
            raise NotFoundError(f"{type} '{name}' not found in library")
        content = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(content)
        return SkillDetail(
            name=meta.get("name", path.stem),
            category=meta.get("category", ""),
            description=meta.get("description", ""),
            built_in=bool(meta.get("built_in", False)),
            type=type,
            content=body,
        )

    def create(self, data: SkillCreate, type: str) -> SkillMeta:
        """Create a new user-defined skill/agent file."""
        directory = self._dir(type)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{data.name}.md"
        if path.exists():
            raise AppError(f"{type} '{data.name}' already exists", status_code=409)
        frontmatter = (
            f"---\nname: {data.name}\ncategory: {data.category}\n"
            f"description: {data.description}\nbuilt_in: false\n---\n"
        )
        path.write_text(frontmatter + data.content, encoding="utf-8")
        return SkillMeta(
            name=data.name,
            category=data.category,
            description=data.description,
            built_in=False,
            type=type,
        )

    def update_content(self, name: str, type: str, content: str) -> None:
        """Update the body of a user-created skill (preserves frontmatter)."""
        path = self._dir(type) / f"{name}.md"
        if not path.exists():
            raise NotFoundError(f"{type} '{name}' not found")
        existing = path.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(existing)
        if meta.get("built_in"):
            raise AppError(f"Built-in {type} '{name}' cannot be edited via API", status_code=403)
        frontmatter = (
            f"---\nname: {meta.get('name', name)}\ncategory: {meta.get('category', '')}\n"
            f"description: {meta.get('description', '')}\nbuilt_in: false\n---\n"
        )
        path.write_text(frontmatter + content, encoding="utf-8")

    async def list_assigned(self, project_id: str) -> list[ProjectSkill]:
        result = await self.session.execute(
            select(ProjectSkill).where(ProjectSkill.project_id == project_id)
        )
        return list(result.scalars().all())

    async def assign(self, project_id: str, project_path: str, name: str, type: str) -> ProjectSkill:
        """Assign a skill to a project: DB record + file copy + CLAUDE.md update."""
        src = self._dir(type) / f"{name}.md"
        if not src.exists():
            raise NotFoundError(f"{type} '{name}' not found in library")

        existing = await self.session.execute(
            select(ProjectSkill).where(
                ProjectSkill.project_id == project_id,
                ProjectSkill.name == name,
                ProjectSkill.type == type,
            )
        )
        if existing.scalar_one_or_none():
            raise AppError(f"{type} '{name}' already assigned to this project", status_code=409)

        dest_dir = Path(project_path) / ".claude" / ("skills" if type == "skill" else "agents")
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_dir / f"{name}.md")

        self._update_claude_md(project_path)

        skill = ProjectSkill(project_id=project_id, name=name, type=type)
        self.session.add(skill)
        await self.session.flush()
        return skill

    async def unassign(self, project_id: str, project_path: str, name: str, type: str) -> None:
        """Remove skill assignment: delete DB record + file + update CLAUDE.md."""
        result = await self.session.execute(
            select(ProjectSkill).where(
                ProjectSkill.project_id == project_id,
                ProjectSkill.name == name,
                ProjectSkill.type == type,
            )
        )
        skill = result.scalar_one_or_none()
        if not skill:
            raise NotFoundError(f"{type} '{name}' not assigned to this project")

        dest = Path(project_path) / ".claude" / ("skills" if type == "skill" else "agents") / f"{name}.md"
        if dest.exists():
            dest.unlink()

        await self.session.delete(skill)
        await self.session.flush()

        self._update_claude_md(project_path)

    def _update_claude_md(self, project_path: str) -> None:
        """Rewrite the Manager AI section of the project's CLAUDE.md."""
        claude_md = Path(project_path) / "CLAUDE.md"

        skills_dir = Path(project_path) / ".claude" / "skills"
        agents_dir = Path(project_path) / ".claude" / "agents"

        skill_lines = []
        if skills_dir.exists():
            for f in sorted(skills_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(content)
                desc = meta.get("description", "")
                skill_lines.append(f"- {f.stem}: {desc}")

        agent_lines = []
        if agents_dir.exists():
            for f in sorted(agents_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(content)
                desc = meta.get("description", "")
                agent_lines.append(f"- {f.stem}: {desc}")

        section_parts = []
        if skill_lines:
            section_parts.append("## Active Skills\n" + "\n".join(skill_lines))
        if agent_lines:
            section_parts.append("## Active Agents\n" + "\n".join(agent_lines))

        if section_parts:
            new_section = (
                f"{MANAGER_AI_MARKER_BEGIN}\n"
                + "\n\n".join(section_parts)
                + "\n\nUse the Skill tool to invoke any of the above when relevant.\n"
                + MANAGER_AI_MARKER_END
            )
        else:
            new_section = ""

        if claude_md.exists():
            existing = claude_md.read_text(encoding="utf-8")
            if MANAGER_AI_MARKER_BEGIN in existing:
                start = existing.index(MANAGER_AI_MARKER_BEGIN)
                end = existing.index(MANAGER_AI_MARKER_END) + len(MANAGER_AI_MARKER_END)
                before = existing[:start].rstrip("\n")
                after = existing[end:].lstrip("\n")
                if new_section:
                    updated = before + ("\n\n" if before else "") + new_section + ("\n\n" + after if after else "")
                else:
                    updated = before + ("\n\n" + after if after else "")
                claude_md.write_text(updated.strip() + "\n", encoding="utf-8")
            else:
                if new_section:
                    claude_md.write_text(existing.rstrip("\n") + "\n\n" + new_section + "\n", encoding="utf-8")
        else:
            if new_section:
                claude_md.write_text(new_section + "\n", encoding="utf-8")

    def get_skills_context(self, project_path: str) -> str:
        """Return a summary string of active skills for use in prompt templates."""
        skills_dir = Path(project_path) / ".claude" / "skills"
        agents_dir = Path(project_path) / ".claude" / "agents"
        lines = []

        if skills_dir.exists():
            for f in sorted(skills_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(content)
                lines.append(f"- Skill '{f.stem}': {meta.get('description', '')}")

        if agents_dir.exists():
            for f in sorted(agents_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(content)
                lines.append(f"- Agent '{f.stem}': {meta.get('description', '')}")

        if not lines:
            return ""
        return "\nActive project skills and agents:\n" + "\n".join(lines)
