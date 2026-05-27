# Implementation Plan: Show Question Under Terminal

**Goal:** Create a `TerminalWithQuestions` wrapper component that stacks `TerminalPanel` + `QuestionCard`s below, used in both the issue detail page and Terminals page.

**Architecture:** New wrapper component composes existing `TerminalPanel` and `QuestionCard`. Fetches pending questions via existing `usePendingQuestions` hook keyed on `terminal.issue_id`. Only renders question section when questions exist. No changes to TerminalPanel or QuestionCard internals.

**Files:**
- Create: `frontend/src/features/terminals/components/terminal-with-questions.tsx`
- Modify: `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`
- Modify: `frontend/src/features/terminals/components/terminal-grid.tsx`

**Tech Stack:** React, TypeScript, TanStack React Query, xterm.js

---

### Task 1: Create TerminalWithQuestions component

**Files:** Create `frontend/src/features/terminals/components/terminal-with-questions.tsx`

- Wrap `TerminalPanel` with pending questions below
- Props: `terminalId`, `projectId`, `issueId`, plus TerminalPanel passthrough (`readOnly?`, `onSessionEnd?`, `onDownloadRecording?`)
- Fetch: `usePendingQuestions(projectId, issueId)`
- Only render question section when `questions.length > 0`
- Question section reuses same markup as current issue page: `<h3>Pending Questions</h3>` + `QuestionCard` list

### Task 2: Update issue detail page

**Files:** Modify `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`

- Replace 3 `<TerminalPanel>` usages in right panel with `<TerminalWithQuestions>`
- Pass `issueId` from terminal object (`terminal1.issue_id`, `terminal2.issue_id`)
- Remove unused `TerminalPanel` import, add `TerminalWithQuestions` import
- Left panel questions stay unchanged

### Task 3: Update TerminalGrid

**Files:** Modify `frontend/src/features/terminals/components/terminal-grid.tsx`

- Replace `<TerminalPanel>` with `<TerminalWithQuestions>`
- Pass `issueId={term.issue_id}` and `projectId={term.project_id}`
- Remove unused `TerminalPanel` import, add `TerminalWithQuestions` import
