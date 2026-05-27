# Show Question Under Terminal

## Goal
Display pending questions below each terminal, both on the issue detail page and on the Terminals page, so questions are visible near every terminal instance.

## Current State
- Issue detail page (`issueId.tsx`): horizontal split. Left panel = IssueDetail + Questions. Right panel = TerminalPanel(s).
- Terminals page (`terminals.tsx`): TerminalGrid with Card header + TerminalPanel per cell.
- Questions are issue-scoped, fetched via `usePendingQuestions(projectId, issueId)`.
- Questions already shown in left panel of issue page and on `/questions` — these stay unchanged.

## Design

### New component: `TerminalWithQuestions`
- **File:** `frontend/src/features/terminals/components/terminal-with-questions.tsx`
- Wraps `TerminalPanel` + pending `QuestionCard`s below it.
- Props: `terminal` (object with `issue_id`), `projectId`, plus all TerminalPanel passthrough props.
- Fetches `usePendingQuestions(projectId, terminal.issue_id)` internally.
- Only renders question section when `questions.length > 0`.
- Question section: small "Pending Questions" header + list of `QuestionCard` components.

### Changes to `issueId.tsx`
- Replace `<TerminalPanel>` in right panel with `<TerminalWithQuestions>`, passing `projectId` and `terminal` as props.
- Left panel questions stay as-is (user explicitly wants them kept).

### Changes to `terminal-grid.tsx`
- Replace `<TerminalPanel>` in grid cells with `<TerminalWithQuestions>`, passing `projectId` and `terminal` as props.

### No changes to
- `QuestionCard` component
- `TerminalPanel` component
- Left-panel question display in `issueId.tsx`
- `/questions` page
- Ask & Brainstorming page

## Edge Cases
- Two terminals for same issue → same questions show under both. Expected behavior.
- No pending questions → question section hidden entirely (no empty header).
- Terminal without `issue_id` → no questions fetched, no section rendered.
