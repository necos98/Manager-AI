## Recap: Refactor `$issueId.tsx` monolith into focused components

### What was done
Full pipeline executed (10 steps):

1. **CodeAnalyzer** — Identified 7 findings: 3x duplicated PendingQuestions JSX, 6x duplicated TerminalWithQuestions, monolithic component (324 lines), excessive nesting, per-branch ErrorBoundary, inline arrow functions.

2. **SpecWriter** — Wrote spec: extract `useTerminalLayout` hook, 3 components (PendingQuestionsSection, TerminalActionBar, TerminalDialogs), single ErrorBoundary, memoized callbacks.

3. **SpecReviewer** — Fixed 3 spec issues: missing `handleSessionEnd`/`handleDownload` returns, wrong TerminalActionBar prop, layout mode naming.

4. **PlanWriter** — 5-step implementation plan with build order dependencies.

5. **PlanReviewer** — Fixed 2 HIGH issues: non-existent `PendingQuestion` type → `Question`, wrong `issueId` prop on PipelineProgress.

6. **TaskWriter** — Created 5 atomic ordered tasks.

7. **Developer** — Implemented all 5 tasks:
   - `useTerminalLayout` hook in hooks.ts (+~60 lines)
   - `PendingQuestionsSection` component (NEW)
   - `TerminalActionBar` component (NEW)
   - `TerminalDialogs` component (NEW)
   - Refactored `$issueId.tsx` (324→174 lines)

8. **CodeReviewer** — PASS (zero correctness/security issues)

9. **QualityReviewer** — PASS (zero BLOCKER/MAJOR, 3 minor findings)

10. **Tester** — PASS. 607 backend tests passed, 33 failures pre-existing. Frontend TypeScript compiles with zero errors.

### Key architectural decisions
- `useTerminalLayout` in existing hooks.ts (not new file)
- Layout mode enum: `issue-only | issue-pipeline | tabs-mode | single-terminal`
- TerminalActionBar triggers dialog open, TerminalDialogs owns kill
- LayoutContent stays in `$issueId.tsx` (only that page uses it)
- `Question` type (not `PendingQuestion` — that type doesn't exist)

### Files changed
- `frontend/src/features/terminals/hooks.ts` — Added React imports + useTerminalLayout export
- `frontend/src/features/questions/components/pending-questions-section.tsx` — NEW
- `frontend/src/features/terminals/components/terminal-action-bar.tsx` — NEW
- `frontend/src/features/terminals/components/terminal-dialogs.tsx` — NEW
- `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` — Refactored (324→174 lines, -150 lines)