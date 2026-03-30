from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.issue_relation import IssueRelationCreate, IssueRelationResponse
from app.services.issue_relation_service import IssueRelationService

router = APIRouter(prefix="/api/issues/{issue_id}/relations", tags=["issue-relations"])


@router.get("", response_model=list[IssueRelationResponse])
async def get_relations(issue_id: str, db: AsyncSession = Depends(get_db)):
    svc = IssueRelationService(db)
    return await svc.get_relations_for_issue(issue_id)


@router.post("", response_model=IssueRelationResponse, status_code=201)
async def add_relation(issue_id: str, data: IssueRelationCreate, db: AsyncSession = Depends(get_db)):
    svc = IssueRelationService(db)
    relation = await svc.add_relation(issue_id, data.target_id, data.relation_type)
    await db.commit()
    return relation


@router.delete("/{relation_id}", status_code=204)
async def delete_relation(issue_id: str, relation_id: int, db: AsyncSession = Depends(get_db)):
    svc = IssueRelationService(db)
    await svc.delete_relation(relation_id, issue_id)
    await db.commit()
