## Summary

Implemented the Structured Question/Answer MCP system enabling Claude to ask users structured questions through Manager AI's UI. The system replaces ad-hoc inline text questions with a consistent MCP tool → UI → answer flow.

## What was built

**Backend:**
- `Question` model (SQLite, question.py) — id, project_id, issue_id, question, options (JSON), status, answer, selected_option, timestamps
- `QuestionStore` singleton — in-memory dict + asyncio.Event per question for efficient blocking MCP tool
- `QuestionService` — create, answer, timeout, get_pending, get_all
- REST API at `/api/questions` — list, pending, count, answer endpoints
- MCP tool `ask_user_question(issue_id, question, options?, timeout_seconds?)` — creates question, emits WebSocket event, blocks on asyncio.Event until answer or timeout
- Alembic migration `04f837ab5823_add_questions_table`

**Frontend:**
- Types: `Question`, `QuestionAnswer` interfaces
- API client: `fetchQuestions`, `fetchPendingQuestions`, `fetchPendingCount`, `answerQuestion`
- React Query hooks: `useQuestions`, `usePendingQuestions`, `usePendingCount`, `useAnswerQuestion`
- `QuestionCard` component — option buttons + free-text input + submit
- Issue page integration — pending questions section below issue detail
- Global `/questions` page — grouped by project with collapsible sections
- Sidebar "Questions" link with pending count badge
- Event context: `question_asked`/`question_answered` as silent events with cache invalidation

**Skill:**
- `claude_resources/skills/asking-questions/SKILL.md` — tells Claude to always use `ask_user_question` MCP tool

## Design decisions
- `asyncio.Event` blocking instead of polling — efficient wait, no CPU waste
- Issue-scoped questions only (every question belongs to an issue)
- Both options AND free-text always available
- Answered questions persist (not auto-deleted)
- Skill follows claude_resources pattern (source of truth, auto-copied to .claude)