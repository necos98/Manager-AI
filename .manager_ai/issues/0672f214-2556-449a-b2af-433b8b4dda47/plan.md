# Implementation Plan: Structured Question/Answer MCP + Global Questions UI

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/models/question.py` | SQLite model |
| `backend/app/services/question_service.py` | Business logic + in-memory QuestionStore with asyncio.Event |
| `backend/app/schemas/question.py` | Pydantic request/response schemas |
| `backend/app/routers/questions.py` | REST API endpoints |
| `frontend/src/features/questions/api.ts` | API client functions |
| `frontend/src/features/questions/hooks.ts` | React Query hooks |
| `frontend/src/features/questions/components/question-card.tsx` | Question display + answer form |
| `frontend/src/routes/questions.tsx` | Global Questions page |
| `claude_resources/skills/asking-questions/SKILL.md` | Skill instructing Claude to use the MCP tool |

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | Register Question model |
| `backend/app/mcp/server.py` | Add `ask_user_question` tool |
| `backend/app/mcp/default_settings.json` | Add tool description |
| `backend/app/main.py` | Register questions router |
| `backend/alembic/env.py` | Import Question model for migration |
| `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` | Add question section below issue detail |
| `frontend/src/shared/components/app-sidebar.tsx` | Add Questions link with badge |
| `frontend/src/shared/context/event-context.tsx` | Handle new event types |
| `frontend/src/shared/types/index.ts` | Add Question types |

---

## Task 1: Backend — Question Model + Database

**Files:**
- Create: `backend/app/models/question.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/alembic/env.py`

Create the SQLite model for questions using the existing SQLAlchemy async ORM pattern.

```python
# backend/app/models/question.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending | answered | timed_out
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_option: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

Register in `__init__.py`:
```python
from app.models.question import Question
# Add "Question" to __all__
```

Update `alembic/env.py`:
```python
from app.models import Project, Task, Question  # add Question
```

---

## Task 2: Backend — QuestionService + QuestionStore

**Files:**
- Create: `backend/app/services/question_service.py`
- Create: `backend/app/schemas/question.py`

In-memory QuestionStore with asyncio.Event for blocking MCP tool. Follows the pattern of MemoryStore (singleton, O(1) lookup).

```python
# backend/app/services/question_service.py
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        q.answered_at = datetime.now(timezone.utc)
        event = self._events.get(question_id)
        if event:
            event.set()
        return q
    
    def timeout(self, question_id: str) -> Question | None:
        q = self._questions.get(question_id)
        if q is None:
            return None
        q.status = "timed_out"
        q.answered_at = datetime.now(timezone.utc)
        event = self._events.get(question_id)
        if event:
            event.set()
        return q
    
    def wait(self, question_id: str, timeout_seconds: int) -> asyncio.Event:
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
        q.answered_at = datetime.now(timezone.utc)
        await self.session.commit()
        question_store.answer(question_id, answer, selected_option)
        return q
    
    async def timeout(self, question_id: str) -> Question | None:
        q = await self.session.get(Question, question_id)
        if q is None:
            return None
        q.status = "timed_out"
        q.answered_at = datetime.now(timezone.utc)
        await self.session.commit()
        question_store.timeout(question_id)
        return q
    
    async def get_pending(self, project_id: str | None = None, issue_id: str | None = None) -> list[Question]:
        if project_id and issue_id:
            return question_store.get_pending_by_issue(project_id, issue_id)
        return question_store.get_all_pending()
    
    async def get_all(self, project_id: str | None = None, issue_id: str | None = None) -> list[Question]:
        stmt = select(Question)
        if project_id:
            stmt = stmt.where(Question.project_id == project_id)
        if issue_id:
            stmt = stmt.where(Question.issue_id == issue_id)
        stmt = stmt.order_by(Question.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def pending_count(self) -> int:
        return len(question_store.get_all_pending())
```

```python
# backend/app/schemas/question.py
from datetime import datetime
from pydantic import BaseModel


class QuestionCreate(BaseModel):
    project_id: str
    issue_id: str
    question: str
    options: list[str] | None = None


class QuestionAnswer(BaseModel):
    answer: str
    selected_option: str | None = None


class QuestionResponse(BaseModel):
    id: str
    project_id: str
    issue_id: str
    question: str
    options: list[str] | None
    status: str
    answer: str | None
    selected_option: str | None
    created_at: datetime | None
    answered_at: datetime | None

    model_config = {"from_attributes": True}
```

---

## Task 3: Backend — REST API Router

**Files:**
- Create: `backend/app/routers/questions.py`
- Modify: `backend/app/main.py`

```python
# backend/app/routers/questions.py
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
```

Register in `main.py`:
```python
from app.routers import ..., questions
app.include_router(questions.router)
```

---

## Task 4: Backend — MCP Tool + Event Emission

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/app/mcp/default_settings.json`

Add `ask_user_question` tool to MCP server. The tool creates a question, emits a WebSocket event, then blocks on asyncio.Event until the user answers or timeout.

```python
# In server.py, add:

from app.services.question_service import QuestionService, question_store

@mcp.tool(description=_desc["tool.ask_user_question.description"])
async def ask_user_question(issue_id: str, question: str, options: list[str] | None = None, timeout_seconds: int = 300) -> dict:
    if not question.strip():
        return {"error": "Question text cannot be empty"}
    if timeout_seconds < 5 or timeout_seconds > 3600:
        return {"error": "Timeout must be between 5 and 3600 seconds"}
    
    async with async_session() as session:
        # Resolve project_id from issue
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_by_id(issue_id)
            project_id = issue.project_id
        except AppError:
            return {"error": "Issue not found"}
        
        qsvc = QuestionService(session)
        q = await qsvc.create(
            project_id=project_id,
            issue_id=issue_id,
            question=question,
            options=options,
        )
        
        # Emit event to frontend
        await event_service.emit({
            "type": "question_asked",
            "question_id": q.id,
            "project_id": project_id,
            "issue_id": issue_id,
            "question": q.question,
            "options": q.options,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    # Block until answer or timeout
    event = question_store.wait(q.id, timeout_seconds)
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        async with async_session() as session:
            await QuestionService(session).timeout(q.id)
        await event_service.emit({
            "type": "question_answered",
            "question_id": q.id,
            "project_id": project_id,
            "issue_id": issue_id,
            "status": "timed_out",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"timed_out": True, "question_id": q.id}
    
    # Answer arrived
    updated = question_store.get(q.id)
    return {
        "question_id": q.id,
        "answer": updated.answer if updated else None,
        "selected_option": updated.selected_option if updated else None,
        "timed_out": False,
    }
```

Add to `default_settings.json`:
```json
"tool.ask_user_question": {
  "name": "ask_user_question",
  "description": "Ask the user a question through the Manager AI interface. Use this EVERY time you need user input — never use inline text questions or AskUserQuestion. The question will appear in the Issue page and the global Questions page. The user can pick an option or write a custom answer. This tool blocks until the user answers or the timeout expires. Parameters: issue_id (required), question (required), options (optional list of strings), timeout_seconds (optional int, default 300)."
}
```

---

## Task 5: Frontend — Types, API Client, Hooks

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Create: `frontend/src/features/questions/api.ts`
- Create: `frontend/src/features/questions/hooks.ts`

Add types:
```typescript
// In shared/types/index.ts, add:
export interface Question {
  id: string;
  project_id: string;
  issue_id: string;
  question: string;
  options: string[] | null;
  status: "pending" | "answered" | "timed_out";
  answer: string | null;
  selected_option: string | null;
  created_at: string | null;
  answered_at: string | null;
}

export interface QuestionAnswer {
  answer: string;
  selected_option: string | null;
}
```

API client:
```typescript
// frontend/src/features/questions/api.ts
import { apiClient } from "@/shared/lib/api-client";
import type { Question, QuestionAnswer } from "@/shared/types";

export async function fetchQuestions(projectId?: string, issueId?: string, status?: string): Promise<Question[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (issueId) params.set("issue_id", issueId);
  if (status) params.set("status", status);
  const res = await apiClient.get(`/api/questions?${params.toString()}`);
  return res.data;
}

export async function fetchPendingQuestions(projectId?: string, issueId?: string): Promise<Question[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (issueId) params.set("issue_id", issueId);
  const res = await apiClient.get(`/api/questions/pending?${params.toString()}`);
  return res.data;
}

export async function fetchPendingCount(): Promise<{ count: number }> {
  const res = await apiClient.get("/api/questions/count");
  return res.data;
}

export async function answerQuestion(questionId: string, data: QuestionAnswer): Promise<Question> {
  const res = await apiClient.post(`/api/questions/${questionId}/answer`, data);
  return res.data;
}
```

Hooks:
```typescript
// frontend/src/features/questions/hooks.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { QuestionAnswer } from "@/shared/types";

export const questionKeys = {
  all: ["questions"] as const,
  pending: ["questions", "pending"] as const,
  count: ["questions", "count"] as const,
  byIssue: (projectId: string, issueId: string) => ["questions", projectId, issueId] as const,
};

export function useQuestions(projectId?: string, issueId?: string) {
  return useQuery({
    queryKey: [...questionKeys.all, projectId, issueId],
    queryFn: () => api.fetchQuestions(projectId, issueId),
  });
}

export function usePendingQuestions(projectId?: string, issueId?: string) {
  return useQuery({
    queryKey: [...questionKeys.pending, projectId, issueId],
    queryFn: () => api.fetchPendingQuestions(projectId, issueId),
    refetchInterval: 30_000,
  });
}

export function usePendingCount() {
  return useQuery({
    queryKey: questionKeys.count,
    queryFn: api.fetchPendingCount,
    refetchInterval: 10_000,
  });
}

export function useAnswerQuestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ questionId, data }: { questionId: string; data: QuestionAnswer }) =>
      api.answerQuestion(questionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: questionKeys.all });
      queryClient.invalidateQueries({ queryKey: questionKeys.pending });
      queryClient.invalidateQueries({ queryKey: questionKeys.count });
    },
  });
}
```

---

## Task 6: Frontend — QuestionCard Component

**Files:**
- Create: `frontend/src/features/questions/components/question-card.tsx`

A card component that shows the question, option buttons, free-text input, and submit. Follows existing UI patterns (Button, Textarea, Card from shadcn/ui).

```tsx
// frontend/src/features/questions/components/question-card.tsx
import { useState } from "react";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { useAnswerQuestion } from "@/features/questions/hooks";
import type { Question } from "@/shared/types";

interface QuestionCardProps {
  question: Question;
}

export function QuestionCard({ question }: QuestionCardProps) {
  const [freeText, setFreeText] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const answerMutation = useAnswerQuestion();

  const isAnswered = question.status !== "pending";

  const handleSubmit = () => {
    const answer = selectedOption || freeText;
    if (!answer.trim()) return;
    answerMutation.mutate({
      questionId: question.id,
      data: { answer, selected_option: selectedOption },
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{question.question}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {question.options && question.options.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {question.options.map((opt) => (
              <Button
                key={opt}
                variant={selectedOption === opt ? "default" : "outline"}
                size="sm"
                disabled={isAnswered}
                onClick={() => setSelectedOption(opt)}
              >
                {opt}
              </Button>
            ))}
          </div>
        )}
        <Textarea
          placeholder="Or write your own answer..."
          value={freeText}
          onChange={(e) => setFreeText(e.target.value)}
          disabled={isAnswered}
          rows={2}
        />
      </CardContent>
      {!isAnswered && (
        <CardFooter className="justify-end">
          <Button
            size="sm"
            disabled={!selectedOption && !freeText.trim() || answerMutation.isPending}
            onClick={handleSubmit}
          >
            {answerMutation.isPending ? "Sending..." : "Answer"}
          </Button>
        </CardFooter>
      )}
      {isAnswered && question.answer && (
        <CardFooter>
          <p className="text-sm text-muted-foreground">
            Answered: {question.answer}
            {question.selected_option && ` (selected: ${question.selected_option})`}
          </p>
        </CardFooter>
      )}
    </Card>
  );
}
```

---

## Task 7: Frontend — Issue Page Integration

**Files:**
- Modify: `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`

Add a pending questions section below the issue detail. Import `usePendingQuestions` hook and `QuestionCard` component.

In the `IssueDetailPage` component, inside the scrollable area (below `<IssueDetail />`), add:

```tsx
import { usePendingQuestions } from "@/features/questions/hooks";
import { QuestionCard } from "@/features/questions/components/question-card";

// Inside the component:
const { data: pendingQuestions } = usePendingQuestions(projectId, issueId);

// Below IssueDetail in the non-terminal view:
{pendingQuestions && pendingQuestions.length > 0 && (
  <div className="border-t mt-6 pt-6 px-4">
    <h3 className="text-sm font-medium mb-3">Pending Questions</h3>
    <div className="space-y-3">
      {pendingQuestions.map((q) => (
        <QuestionCard key={q.id} question={q} />
      ))}
    </div>
  </div>
)}
```

---

## Task 8: Frontend — Global Questions Page

**Files:**
- Create: `frontend/src/routes/questions.tsx`

Follows the Terminals page pattern. Groups pending questions by project.

```tsx
// frontend/src/routes/questions.tsx
import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { HelpCircle } from "lucide-react";
import { usePendingQuestions } from "@/features/questions/hooks";
import { useProjects } from "@/features/projects/hooks";
import { QuestionCard } from "@/features/questions/components/question-card";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/shared/components/ui/collapsible";

export const Route = createFileRoute("/questions")({
  component: QuestionsPage,
});

function QuestionsPage() {
  const { data: questions, isLoading } = usePendingQuestions();
  const { data: projects } = useProjects();

  useEffect(() => {
    document.title = "Questions - Manager AI";
  }, []);

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-48" />
        {[1, 2].map((i) => <Skeleton key={i} className="h-32" />)}
      </div>
    );
  }

  // Group questions by project
  const grouped: Record<string, typeof questions> = {};
  for (const q of questions ?? []) {
    (grouped[q.project_id] ??= []).push(q);
  }

  const getProjectName = (projectId: string) =>
    projects?.find((p) => p.id === projectId)?.name ?? projectId;

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <h1 className="text-xl font-semibold">Questions</h1>
        <span className="text-sm text-muted-foreground">
          {questions?.length ?? 0} pending
        </span>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {Object.keys(grouped).length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <HelpCircle className="size-10 mb-3" />
            <p>No pending questions</p>
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(grouped).map(([projectId, qs]) => (
              <Collapsible key={projectId} defaultOpen>
                <CollapsibleTrigger className="text-sm font-medium mb-2 flex items-center gap-1">
                  {getProjectName(projectId)}
                  <span className="text-xs text-muted-foreground">({qs?.length ?? 0})</span>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-3 pt-2">
                  {qs?.map((q) => <QuestionCard key={q.id} question={q} />)}
                </CollapsibleContent>
              </Collapsible>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## Task 9: Frontend — Sidebar Link + Event Context

**Files:**
- Modify: `frontend/src/shared/components/app-sidebar.tsx`
- Modify: `frontend/src/shared/context/event-context.tsx`

Add Questions link to sidebar Global section (after Terminals):
```tsx
// Import HelpCircle icon
import { ..., HelpCircle } from "lucide-react";
// Import usePendingCount
import { usePendingCount } from "@/features/questions/hooks";

// In AppSidebar component:
const { data: pendingQuestionsCount } = usePendingCount();
const questionsPendingCount = pendingQuestionsCount?.count ?? 0;

// Add after Terminals link:
<SidebarMenuItem>
  <SidebarMenuButton
    asChild
    isActive={!!matchRoute({ to: "/questions", fuzzy: true })}
  >
    <Link to="/questions">
      <HelpCircle />
      <span>Questions</span>
    </Link>
  </SidebarMenuButton>
  {questionsPendingCount > 0 && (
    <SidebarMenuBadge>{questionsPendingCount}</SidebarMenuBadge>
  )}
</SidebarMenuItem>
```

In `event-context.tsx`, add `question_asked` and `question_answered` to the silent events in `buildToastContent`:
```tsx
case "question_asked":
case "question_answered":
    // Silent — handled by React Query invalidation
    break;
```

And add cache invalidation for these event types in the WebSocket handler:
```tsx
// In the event handler, invalidate question queries:
case "question_asked":
case "question_answered":
  queryClient.invalidateQueries({ queryKey: ["questions"] });
  break;
```

---

## Task 10: Skill File

**Files:**
- Create: `claude_resources/skills/asking-questions/SKILL.md`

```markdown
---
name: asking-questions
description: Use when you need to ask the user a question or get their input on a decision. Tells Claude to use the ask_user_question MCP tool instead of inline text or AskUserQuestion.
---

# Asking Questions to the User

## The Rule

**ALWAYS use the `ask_user_question` MCP tool when you need user input.** Never use inline text questions or `AskUserQuestion`.

## When to Use

Use `ask_user_question` whenever:
- You need the user to make a decision between options
- You need clarification on requirements
- You want to confirm an approach before proceeding
- You hit a blocker that requires user input

## How to Use

```
ask_user_question(issue_id, question, options?, timeout_seconds?)
```

### Parameters

- `issue_id` (required): The ID of the current issue you're working on
- `question` (required): Clear, concise question text
- `options` (optional): List of 2-4 possible answers. Always provide options when choices are clear.
- `timeout_seconds` (optional): How long to wait for an answer (default 300s / 5 min)

### Best Practices

1. **Always provide options** when the user faces a clear choice (2-4 options)
2. **Allow free-text** — the user can always write a custom answer instead of picking an option
3. **Be specific** — don't ask "What should I do?" but "Which library should we use for date formatting?"
4. **One question at a time** — don't batch multiple questions
5. **Wait for the answer** — the tool blocks until the user responds, then continue

### Example

```python
# Good — specific question with options
ask_user_question(
    issue_id="abc-123",
    question="Which authentication method should we use?",
    options=["JWT tokens", "Session cookies", "OAuth 2.0"]
)

# Also good — open-ended when needed
ask_user_question(
    issue_id="abc-123",
    question="What should the rate limit be for this endpoint?"
)
```

### What the User Sees

Your question appears in:
1. The Issue page (under the issue detail)
2. The global Questions page (grouped by project)

The user can click an option button or type a custom answer. The tool waits until they respond.
```

---

## Task 11: Alembic Migration + Final Wiring

**Files:**
- Create: Migration via `alembic revision --autogenerate`
- Modify: `backend/app/mcp/default_settings.json` (tool description added in Task 4)

Generate and run the migration:
```bash
cd backend
python -m alembic revision --autogenerate -m "add questions table"
python -m alembic upgrade head
```

Verify:
- Backend starts without errors
- GET /api/questions returns []
- MCP tool appears in tool list
- Frontend builds without TypeScript errors
- Questions page renders empty state