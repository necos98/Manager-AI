from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models.issue_relation import IssueRelation, RelationType


class IssueRelationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_relation(
        self, source_id: str, target_id: str, relation_type: RelationType
    ) -> IssueRelation:
        if source_id == target_id:
            raise ValidationError("Un'issue non può essere collegata a se stessa")

        # Normalize RELATED: source_id < target_id alphabetically
        if relation_type == RelationType.RELATED and source_id > target_id:
            source_id, target_id = target_id, source_id

        # Cycle detection (only for BLOCKS)
        if relation_type == RelationType.BLOCKS:
            if await self._detect_cycle(source_id, target_id):
                raise ValidationError("Aggiungere questa relazione creerebbe una dipendenza circolare")

        relation = IssueRelation(source_id=source_id, target_id=target_id, relation_type=relation_type)
        self.session.add(relation)
        await self.session.flush()
        return relation

    async def _detect_cycle(self, source_id: str, target_id: str) -> bool:
        """Return True if adding source->target BLOCKS would create a cycle."""
        visited: set[str] = set()
        queue = [target_id]
        while queue:
            current = queue.pop(0)
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            result = await self.session.execute(
                select(IssueRelation.target_id)
                .where(IssueRelation.source_id == current)
                .where(IssueRelation.relation_type == RelationType.BLOCKS)
            )
            queue.extend(result.scalars().all())
        return False

    async def get_relations_for_issue(self, issue_id: str) -> list[IssueRelation]:
        result = await self.session.execute(
            select(IssueRelation).where(
                or_(IssueRelation.source_id == issue_id, IssueRelation.target_id == issue_id)
            )
        )
        return list(result.scalars().all())

    async def get_blockers(self, issue_id: str) -> list[IssueRelation]:
        """Return BLOCKS relations where this issue is the target (i.e., it is blocked)."""
        result = await self.session.execute(
            select(IssueRelation)
            .where(IssueRelation.target_id == issue_id)
            .where(IssueRelation.relation_type == RelationType.BLOCKS)
        )
        return list(result.scalars().all())

    async def get_by_id(self, relation_id: int) -> IssueRelation:
        rel = await self.session.get(IssueRelation, relation_id)
        if rel is None:
            raise NotFoundError("Relazione non trovata")
        return rel

    async def delete_relation(self, relation_id: int, requesting_issue_id: str) -> None:
        rel = await self.get_by_id(relation_id)
        if rel.source_id != requesting_issue_id and rel.target_id != requesting_issue_id:
            raise NotFoundError("Relazione non trovata")
        await self.session.delete(rel)
        await self.session.flush()
