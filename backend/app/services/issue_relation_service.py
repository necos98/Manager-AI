"""File-backed IssueRelationService.

Relations live in each source issue's issue.yaml (canonical side).
RELATED edges are normalized so the alphabetically-smaller id owns
the record. BLOCKS cycle detection scans the file store for transitive
paths instead of issuing SQL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models.issue_relation import RelationType
from app.services.project_service import ProjectService
from app.storage import issue_store
from app.storage.issue_store import RelationRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep="T", timespec="microseconds")


@dataclass
class RelationView:
    """Resolved relation with explicit source/target for API responses."""
    source_id: str
    target_id: str
    relation_type: str
    created_at: str


class IssueRelationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _all_paths(self) -> list[str]:
        projects = await ProjectService(self.session).list_all(archived=None)
        return [p.path for p in projects]

    async def _find_issue_path(self, issue_id: str) -> str | None:
        for path in await self._all_paths():
            if issue_store.issue_exists(path, issue_id):
                return path
        return None

    async def add_relation(
        self, source_id: str, target_id: str, relation_type: RelationType
    ) -> RelationView:
        if source_id == target_id:
            raise ValidationError("Un'issue non può essere collegata a se stessa")

        rtype_value = relation_type.value if isinstance(relation_type, RelationType) else str(relation_type)

        # Normalize RELATED: source_id < target_id alphabetically
        if rtype_value == RelationType.RELATED.value and source_id > target_id:
            source_id, target_id = target_id, source_id

        # Cycle detection for BLOCKS
        if rtype_value == RelationType.BLOCKS.value:
            if await self._detect_cycle(source_id, target_id):
                raise ValidationError(
                    "Aggiungere questa relazione creerebbe una dipendenza circolare"
                )

        source_path = await self._find_issue_path(source_id)
        if source_path is None:
            raise NotFoundError("Issue not found")
        rel = RelationRecord(target_id=target_id, type=rtype_value, created_at=_now_iso())
        issue_store.upsert_relation(source_path, source_id, rel)
        return RelationView(
            source_id=source_id,
            target_id=target_id,
            relation_type=rtype_value,
            created_at=rel.created_at,
        )

    async def get_relations_for_issue(self, issue_id: str) -> list[RelationView]:
        out: list[RelationView] = []
        for path in await self._all_paths():
            for issue in issue_store.list_issues_full(path):
                for rel in issue.relations:
                    if issue.id == issue_id or rel.target_id == issue_id:
                        out.append(
                            RelationView(
                                source_id=issue.id,
                                target_id=rel.target_id,
                                relation_type=rel.type,
                                created_at=rel.created_at,
                            )
                        )
        return out

    async def get_blockers(self, issue_id: str) -> list[RelationView]:
        out: list[RelationView] = []
        for path in await self._all_paths():
            for issue in issue_store.list_issues_full(path):
                for rel in issue.relations:
                    if rel.target_id == issue_id and rel.type == RelationType.BLOCKS.value:
                        out.append(
                            RelationView(
                                source_id=issue.id,
                                target_id=rel.target_id,
                                relation_type=rel.type,
                                created_at=rel.created_at,
                            )
                        )
        return out

    async def delete_relation(self, relation_id: str, requesting_issue_id: str) -> None:
        """Delete a relation by its deterministic hash id. Caller must own
        either side of the relation."""
        from app.schemas.issue_relation import make_relation_id

        candidates: list[tuple[str, str, str, str]] = []
        for path in await self._all_paths():
            for issue in issue_store.list_issues_full(path):
                for rel in issue.relations:
                    candidates.append((path, issue.id, rel.target_id, rel.type))

        for path, src, tgt, rtype in candidates:
            if make_relation_id(src, tgt, rtype) == relation_id:
                if requesting_issue_id not in (src, tgt):
                    raise NotFoundError("Relazione non trovata")
                issue_store.remove_relation(path, src, tgt, rtype)
                return
        raise NotFoundError("Relazione non trovata")

    async def _detect_cycle(self, source_id: str, target_id: str) -> bool:
        """Return True if adding source→target BLOCKS would cycle back to source."""
        visited: set[str] = set()
        queue: list[str] = [target_id]
        while queue:
            current = queue.pop(0)
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            # Find outgoing BLOCKS relations of `current` across all projects
            for path in await self._all_paths():
                issue = issue_store.load_issue(path, current)
                if issue is None:
                    continue
                for rel in issue.relations:
                    if rel.type == RelationType.BLOCKS.value:
                        queue.append(rel.target_id)
        return False
