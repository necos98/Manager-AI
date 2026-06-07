## Summary
Fixed duplicate questions dialog on issue detail page by adding `hideQuestions` prop to `TerminalWithQuestions`.

## What was done
- Added optional `hideQuestions` boolean prop (default false) to `TerminalWithQuestions`
- Gated questions rendering block with `!hideQuestions`
- Passed `hideQuestions={true}` to all 6 call sites in `$issueId.tsx` (all layout states)
- Standalone `/terminals` page unchanged — questions still show there

## Files changed
- `frontend/src/features/terminals/components/terminal-with-questions.tsx`
- `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`

## Test results
606/637 backend tests passed. 31 pre-existing failures — none related to this frontend-only change. No regressions.