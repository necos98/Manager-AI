# Enrich Questions Page with Issue and Project Context

## Goal
On the global Questions page and in QuestionCard components, show the issue and project each question belongs to, plus useful metadata (status, timestamps, navigation link).

## Current State
- `QuestionCard` shows only question text, options, and answer input — no project/issue context
- Global Questions page (`/questions`) groups by project in collapsible sections but individual cards lack issue info
- `QuestionResponse` schema includes `project_id` and `issue_id` but not the human-readable names
- Issue detail page already shows questions in context — no change needed there

## Requirements

### R1: Show issue reference on each question card
- Display the issue name on the QuestionCard
- Make it a clickable link navigating to the issue detail page

### R2: Show project reference on each question card
- Display the project name on the QuestionCard
- Show as a muted text badge

### R3: Status badge
- Color-coded badge: pending (amber/yellow), answered (green), timed_out (gray)
- Visible on every question card

### R4: Timestamps
- Show "Asked X ago" relative time
- Show "Answered X ago" when status is answered (instead of or in addition to "Asked")
- Use relative time format for readability

## Implementation Plan

### Backend

**Schema** (`backend/app/schemas/question.py`):
- Add `project_name: str | None` and `issue_name: str | None` to `QuestionResponse`

**Service** (`backend/app/services/question_service.py`):
- `get_all()`: JOIN `issues` and `projects` tables, include `issues.name AS issue_name` and `projects.name AS project_name` in the query
- `get_pending()`: reads from in-memory `QuestionStore`; populate names from DB when loading into store, or enrich on read

**Query pattern**:
```sql
SELECT q.*, i.name AS issue_name, p.name AS project_name
FROM questions q
LEFT JOIN issues i ON q.issue_id = i.id
LEFT JOIN projects p ON q.project_id = p.id
ORDER BY q.created_at DESC
```

### Frontend

**Types** (`frontend/src/shared/types/index.ts`):
- Add optional `project_name?: string` and `issue_name?: string` to `Question` interface

**QuestionCard** (`frontend/src/features/questions/components/question-card.tsx`):
- Add metadata header row above the question text:
  - Status badge (left-aligned): colored pill with status text
  - Project name (center/right): muted text badge
- Add issue link row: clickable issue name → `/#/projects/{project_id}/issues/{issue_id}`
- Add timestamp row: relative time display

**Global Questions page** (`frontend/src/routes/questions.tsx`):
- With enriched cards, the project grouping can remain as-is or be simplified since each card now shows context
- Keep collapsible project sections for organization

### Status Badge Colors
| Status | Color | Label |
|--------|-------|-------|
| pending | amber/yellow | Pending |
| answered | green | Answered |
| timed_out | gray | Timed Out |

### What Stays Unchanged
- MCP `ask_user_question` tool
- WebSocket events (`question_asked`, `question_answered`)
- `QuestionStore` in-memory cache pattern
- Issue detail page questions section
- Sidebar pending count badge
- Question answering flow (POST /api/questions/{id}/answer)
