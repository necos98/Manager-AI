# Structured Question/Answer MCP + Global Questions UI

## Overview

Create a structured system for Claude to ask questions to the user through Manager AI's UI, replacing ad-hoc inline text questions. Claude calls an MCP tool that blocks until the user answers via a dedicated frontend interface. Questions appear both in the Issue page and in a global "Questions" page (like Terminals).

## Motivation

Currently Claude has no consistent method for interacting with the user:
- Sometimes writes questions inline with options in text
- Sometimes uses `AskUserQuestion` (Claude Code built-in)
- No structured, persistent question workflow

This creates a fragmented experience. The user wants a single, reliable path: Claude always uses an MCP tool → Manager AI displays the question in a structured UI → user answers → Claude gets the answer back.

## Functional Requirements

### MCP Tool: `ask_user_question`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_id` | string | Yes | Issue the question relates to |
| `question` | string | Yes | The question text |
| `options` | list[string] | No | Multiple choice options. Empty = free-text only |
| `timeout_seconds` | int | No | Max wait time, default 300s (5 min) |

**Behavior:**
- Creates a Question record (status=pending)
- Emits `question_asked` WebSocket event
- Awaits user answer via `asyncio.Event` (efficient, no polling)
- Returns `{answer, selected_option}` or `{timed_out: true}` on timeout
- User can pick an option OR write a custom free-text answer (both modes always available)

### Backend

**Model** — `Question` (SQLite table):
- `id` (UUID, PK)
- `project_id` (FK → projects)
- `issue_id` (FK → issues)
- `question` (text)
- `options` (JSON array, nullable)
- `status` (enum: pending, answered, timed_out)
- `answer` (text, nullable — user's free-text response)
- `selected_option` (text, nullable — the option picked, if any)
- `created_at` (datetime)
- `answered_at` (datetime, nullable)

**In-Memory Store** — `QuestionStore` singleton:
- `Dict[id, asyncio.Event]` for efficient blocking wait
- O(1) lookup for pending questions by project/issue
- Writes async to SQLite via background worker (follow existing memory pattern)

**Service** — `QuestionService`:
- `create(project_id, issue_id, question, options)` → Question
- `answer(question_id, answer, selected_option)` → marks answered, signals event
- `get_pending(project_id, issue_id)` → list pending questions
- `timeout(question_id)` → marks timed_out, signals event

**REST API** — `/api/questions`:
- `GET /api/questions?project_id=X&issue_id=Y` — list questions with filters
- `GET /api/questions/pending` — all pending questions globally (for global page)
- `POST /api/questions/{id}/answer` — submit answer
- `GET /api/questions/count` — pending count (for sidebar badge)

**WebSocket Events:**
- `question_asked`: {question_id, project_id, issue_id, question, options}
- `question_answered`: {question_id, project_id, issue_id, answer, selected_option}

### Frontend

**Issue Page** — Question section below issue detail:
- Lists pending questions for current issue
- Each question shows: text, option buttons, free-text input, submit button
- Answered questions show answer (read-only history)
- Auto-updates via WebSocket events

**Global Questions Page** — `/questions` route:
- Groups pending questions by project (collapsible sections)
- Same QuestionCard component as issue page
- Pattern follows Terminals page (global view, project grouping)
- Badge in sidebar showing pending count

**Sidebar** — Add "Questions" link under Global section:
- Icon: `HelpCircle` (lucide)
- Badge: pending questions count (like Terminals count badge)

### Skill File

**Location:** `claude_resources/skills/asking-questions/SKILL.md`

**Content:**
- Tells Claude to ALWAYS use `ask_user_question` MCP tool when needing user input
- Never use inline text questions or `AskUserQuestion`
- Always provide options when possible (2-4 choices), but always allow free-text
- Always provide the issue_id of the current issue
- Wait for the answer before proceeding

## Non-Functional Requirements

- **Performance:** Question creation <50ms, event delivery <200ms
- **Timeout:** Default 300s, configurable per-call
- **Persistence:** Answered questions kept for history (not auto-deleted)
- **No new infrastructure:** Uses existing SQLite + asyncio.Event pattern

## Out of Scope

- Multi-question batches (one question at a time)
- Question editing/deletion by user
- Question threads/conversations
- Email/push notifications for questions
- Question templates or saved questions

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| `asyncio.Event` blocking | More efficient than polling loop. No CPU waste. Timeout via `asyncio.wait_for`. |
| SQLite + in-memory | Follows existing project patterns. Simpler than YAML files for transient data. |
| Issue-scoped only | User confirmed. Every question belongs to an issue. |
| Single blocking MCP call | User confirmed. Claude waits for answer synchronously. |
| Both options + free-text always | Maximum flexibility. User can pick option or type custom response. |
| Skill in `claude_resources/` | Follows existing project convention for distributable skills. |