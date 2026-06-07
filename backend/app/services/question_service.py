import asyncio
import uuid

from app.utils.datetime import now
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.issue import Issue
from app.models.project import Project
from app.models.question import Question


class QuestionStore:
    """In-memory singleton for fast question lookup + asyncio.Event waiting."""

    def __init__(self):
        self._questions: dict[str, Question] = {}
        self._events: dict[str, asyncio.Event] = {}

    def put(self, question: Question) -> asyncio.Event:
        self._questions[question.id] = question
        event = asyncio.Event()
        self._events[question.id] = event
        return event

    def get(self, question_id: str) -> Question | None:
        return self._questions.get(question_id)

    def answer(self, question_id: str, answer: str, selected_option: str | None) -> Question | None:
        q = self._questions.get(question_id)
        if q is None:
            return None
        q.status = "answered"
        q.answer = answer
        q.selected_option = selected_option
        q.answered_at = now()
        event = self._events.get(question_id)
        if event:
            event.set()
        return q

    def timeout(self, question_id: str) -> Question | None:
        q = self._questions.get(question_id)
        if q is None:
            return None
        q.status = "timed_out"
        q.answered_at = now()
        event = self._events.get(question_id)
        if event:
            event.set()
        return q

    def wait(self, question_id: str) -> asyncio.Event | None:
        return self._events.get(question_id)

    def get_pending_by_issue(self, project_id: str, issue_id: str) -> list[Question]:
        return [
            q for q in self._questions.values()
            if q.project_id == project_id and q.issue_id == issue_id and q.status == "pending"
        ]

    def get_all_pending(self) -> list[Question]:
        return [q for q in self._questions.values() if q.status == "pending"]


question_store = QuestionStore()


class QuestionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project_id: str, issue_id: str, question: str, options: list[str] | None) -> Question:
        q = Question(
            id=str(uuid.uuid4()),
            project_id=project_id,
            issue_id=issue_id,
            question=question,
            options=options,
            status="pending",
        )
        self.session.add(q)
        await self.session.commit()
        await self.session.refresh(q)
        question_store.put(q)
        return q

    async def answer_question(self, question_id: str, answer: str, selected_option: str | None) -> Question | None:
        q = await self.session.get(Question, question_id)
        if q is None:
            return None
        q.status = "answered"
        q.answer = answer
        q.selected_option = selected_option
        q.answered_at = now()
        await self.session.commit()
        question_store.answer(question_id, answer, selected_option)
        return q

    async def timeout(self, question_id: str) -> Question | None:
        q = await self.session.get(Question, question_id)
        if q is None:
            return None
        q.status = "timed_out"
        q.answered_at = now()
        await self.session.commit()
        question_store.timeout(question_id)
        return q

    async def get_pending(self, project_id: str | None = None, issue_id: str | None = None) -> list[Question]:
        if project_id and issue_id:
            questions = question_store.get_pending_by_issue(project_id, issue_id)
        else:
            questions = question_store.get_all_pending()

        if questions:
            issue_ids = list({q.issue_id for q in questions})
            project_ids = list({q.project_id for q in questions})

            issue_stmt = select(Issue.id, Issue.name).where(Issue.id.in_(issue_ids))
            project_stmt = select(Project.id, Project.name).where(Project.id.in_(project_ids))

            issue_result = await self.session.execute(issue_stmt)
            issue_names = {row[0]: row[1] for row in issue_result.all()}

            project_result = await self.session.execute(project_stmt)
            project_names = {row[0]: row[1] for row in project_result.all()}

            for q in questions:
                q.issue_name = issue_names.get(q.issue_id)
                q.project_name = project_names.get(q.project_id)

        return questions

    async def get_all(self, project_id: str | None = None, issue_id: str | None = None) -> list[Question]:
        stmt = (
            select(Question, Issue.name, Project.name)
            .outerjoin(Issue, Question.issue_id == Issue.id)
            .outerjoin(Project, Question.project_id == Project.id)
        )
        if project_id:
            stmt = stmt.where(Question.project_id == project_id)
        if issue_id:
            stmt = stmt.where(Question.issue_id == issue_id)
        stmt = stmt.order_by(Question.created_at.desc())
        result = await self.session.execute(stmt)
        questions = []
        for q, issue_name, project_name in result.all():
            q.issue_name = issue_name
            q.project_name = project_name
            questions.append(q)
        return questions

    async def pending_count(self) -> int:
        return len(question_store.get_all_pending())
