# Notify user when model asks a question via ask_user_question tool

## Problem

When the AI model calls `ask_user_question` MCP tool, a `question_asked` WebSocket event is emitted. The frontend treats this event as **silent** (no toast, no sound) — it only triggers query cache invalidation for the questions list. The user has no alert that a question is waiting, unless they manually navigate to the Questions page.

Other triggers (milestones, errors, completions) use `send_notification` which emits a `notification` event → frontend shows toast + plays sound. The questions tool lacks this.

## Solution

In `ask_user_question` (backend `app/mcp/server.py`), after emitting the existing `question_asked` event, also emit a `notification` type event with:
- **title**: "New question from AI"
- **message**: the question text
- **project_id**, **issue_id**, **issue_name**, **project_name**: same metadata as `send_notification`

This reuses the existing notification infrastructure — no frontend changes needed.

### Affected code

- `backend/app/mcp/server.py` — `ask_user_question` function (~lines 1166–1200)
  - Fetch `project_name` via `ProjectService` (same pattern as `send_notification` at line 334)
  - Fetch `issue_name` from already-loaded `issue` object
  - Emit `notification` event after `question_asked` event

### No changes

- Frontend: no changes needed. `notification` event already handled with toast + sound.
- `question_asked` event: stays silent (data-sync only).
- `QuestionService` / `question_service.py`: no changes.

### Behavior

- AI asks question → `question_asked` event (data sync) + `notification` event (toast + sound)
- User clicks notification → navigates to issue → answers question
- Same flow as any other notification