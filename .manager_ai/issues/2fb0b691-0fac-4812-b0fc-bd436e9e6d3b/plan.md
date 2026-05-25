# Notify on ask_user_question — Implementation Plan

**Goal:** Emit a `notification` event when the AI asks the user a question, so the user gets a toast + sound alert.

**Architecture:** Add a `notification` event emit inside `ask_user_question` in `server.py`, right after the existing `question_asked` event. Reuses the existing notification infrastructure — no frontend changes.

**Files:**
- Modify: `backend/app/mcp/server.py` — `ask_user_question` function (lines 1189-1197)

## Implementation

After the `question_asked` event emit block (line 1197), add:

1. Derive `issue_name` from already-fetched `issue` object
2. Fetch `project` via `ProjectService(session).get_by_id(project_id)`
3. Emit `notification` event with title "New question from AI" and message = `question` text

All variables already in scope: `session`, `project_id`, `issue_id`, `issue`, `question`. `ProjectService` already imported.