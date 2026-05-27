# Implementation Plan: Enrich Questions Page

## Task 1: Backend — Add project_name and issue_name to API responses

**Files:**
- Modify: `backend/app/schemas/question.py`
- Modify: `backend/app/services/question_service.py`

### Step 1: Update QuestionResponse schema

Add `project_name` and `issue_name` as optional fields to `QuestionResponse` in `backend/app/schemas/question.py`:

```python
class QuestionResponse(BaseModel):
    id: str
    project_id: str
    issue_id: str
    project_name: str | None = None
    issue_name: str | None = None
    question: str
    options: list[str] | None
    status: str
    answer: str | None
    selected_option: str | None
    created_at: datetime | None
    answered_at: datetime | None

    model_config = {"from_attributes": True}
```

### Step 2: Enrich get_all() with JOINs

Modify `get_all()` in `backend/app/services/question_service.py` to JOIN issues and projects tables and attach names to Question objects:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from app.models.issue import Issue
from app.models.project import Project

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
    rows = result.all()
    questions = []
    for q, issue_name, project_name in rows:
        q.issue_name = issue_name
        q.project_name = project_name
        questions.append(q)
    return questions
```

### Step 3: Enrich get_pending() with names

Modify `get_pending()` to resolve project/issue names for in-memory questions:

```python
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
```

---

## Task 2: Frontend — Enrich QuestionCard with metadata

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Modify: `frontend/src/features/questions/components/question-card.tsx`

### Step 1: Update Question type

In `frontend/src/shared/types/index.ts`, add optional fields:

```typescript
export interface Question {
  id: string;
  project_id: string;
  issue_id: string;
  project_name?: string;
  issue_name?: string;
  question: string;
  options: string[] | null;
  status: "pending" | "answered" | "timed_out";
  answer: string | null;
  selected_option: string | null;
  created_at: string | null;
  answered_at: string | null;
}
```

### Step 2: Update QuestionCard component

Rewrite `QuestionCard` in `frontend/src/features/questions/components/question-card.tsx` to include:
- Metadata header: status badge + project name + timestamps
- Clickable issue link (navigates to issue detail page)
- Keep existing question text, options, and answer input

```tsx
import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { Card, CardContent, CardFooter, CardHeader } from "@/shared/components/ui/card";
import { MarkdownViewer } from "@/shared/components/markdown-viewer";
import { useAnswerQuestion } from "@/features/questions/hooks";
import type { Question } from "@/shared/types";

interface QuestionCardProps {
  question: Question;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  pending: { label: "Pending", className: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" },
  answered: { label: "Answered", className: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300" },
  timed_out: { label: "Timed Out", className: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400" },
};

export function QuestionCard({ question }: QuestionCardProps) {
  const [freeText, setFreeText] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const answerMutation = useAnswerQuestion();

  const isAnswered = question.status !== "pending";
  const statusCfg = statusConfig[question.status];

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
      <CardHeader className="pb-2">
        {/* Metadata row */}
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusCfg.className}`}>
            {statusCfg.label}
          </span>
          {question.project_name && (
            <span className="text-xs text-muted-foreground">{question.project_name}</span>
          )}
        </div>
        {/* Issue link */}
        {question.issue_name && (
          <Link
            to="/projects/$projectId/issues/$issueId"
            params={{ projectId: question.project_id, issueId: question.issue_id }}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Issue: {question.issue_name}
          </Link>
        )}
        {/* Timestamps */}
        <div className="text-xs text-muted-foreground">
          {question.created_at && (
            <span>Asked {formatDistanceToNow(new Date(question.created_at + "Z"), { addSuffix: true })}</span>
          )}
          {question.answered_at && question.status !== "pending" && (
            <span> &middot; Answered {formatDistanceToNow(new Date(question.answered_at + "Z"), { addSuffix: true })}</span>
          )}
        </div>
        <MarkdownViewer content={question.question} />
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
            disabled={(!selectedOption && !freeText.trim()) || answerMutation.isPending}
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

## Task 3: Verify and Commit

- Start the backend and frontend, verify the Questions page shows enriched cards
- Run backend tests: `cd backend && python -m pytest tests/ -v`
- Commit with a descriptive message
