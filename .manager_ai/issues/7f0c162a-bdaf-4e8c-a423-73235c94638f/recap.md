Created `TerminalWithQuestions` wrapper component in `frontend/src/features/terminals/components/terminal-with-questions.tsx`. This component composes `TerminalPanel` + pending `QuestionCard`s below it, fetching questions via `usePendingQuestions(projectId, issueId)` and only rendering the question section when questions exist.

Updated `issueId.tsx`: replaced all 3 `TerminalPanel` usages (single terminal, two-terminal split) with `TerminalWithQuestions`, passing `issueId` from the terminal object.

Updated `terminal-grid.tsx`: replaced `TerminalPanel` usage in grid cells with `TerminalWithQuestions`, passing `issueId={term.issue_id}`.

Left panel questions in `issueId.tsx` unchanged. `/questions` page unchanged. `QuestionCard` and `TerminalPanel` internals unchanged.