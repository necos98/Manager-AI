from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.question import QuestionAnswer, QuestionResponse
from app.services.question_service import QuestionService

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=list[QuestionResponse])
async def list_questions(
    project_id: str | None = None,
    issue_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    svc = QuestionService(db)
    questions = await svc.get_all(project_id=project_id, issue_id=issue_id)
    if status:
        questions = [q for q in questions if q.status == status]
    return questions


@router.get("/pending", response_model=list[QuestionResponse])
async def list_pending_questions(
    project_id: str | None = None,
    issue_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    svc = QuestionService(db)
    return await svc.get_pending(project_id=project_id, issue_id=issue_id)


@router.get("/count")
async def pending_count(db: AsyncSession = Depends(get_db)):
    svc = QuestionService(db)
    return {"count": await svc.pending_count()}


@router.post("/{question_id}/answer", response_model=QuestionResponse)
async def answer_question(
    question_id: str,
    data: QuestionAnswer,
    db: AsyncSession = Depends(get_db),
):
    svc = QuestionService(db)
    q = await svc.answer_question(question_id, data.answer, data.selected_option)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return q
