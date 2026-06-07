# Specification: Refactor `$issueId.tsx` Monolith Into Focused Components

## Scope

Decompose `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` (324 lines, single monolithic `IssueDetailPage` component) into smaller, single-responsibility components and a custom hook. The file manages 7 data hooks, 2 mutations, terminal lifecycle, split-view layout, pipeline progress, pending questions, and 2 dialogs — violating Single Responsibility Principle and producing 6x duplicated `TerminalWithQuestions` renderings and 3x duplicated `PendingQuestions` blocks.

## Goals

1. Reduce `IssueDetailPage` to ~80 lines — orchestration only, no raw state or layout logic
2. Eliminate all duplicated JSX blocks
3. Add single top-level `ErrorBoundary` (replace current 4 per-branch instances)
4. Memoize callback props to prevent unnecessary re-renders
5. Preserve every existing behavior — no visual or functional changes

## Non-Goals

- No changes to backend
- No changes to `TerminalWithQuestions`, `TerminalPanel`, `PipelineProgress`, `IssueDetail`, or `QuestionCard` components
- No style/UI redesign
- No test additions (existing tests must still pass)

## Proposed Architecture

### 1. Extract `useTerminalLayout` hook
**File:** `frontend/src/features/terminals/hooks.ts` (add to existing file, already holds `useTerminals`, `useCreateTerminal`, `useKillTerminal`, etc.)

Encapsulate all terminal lifecycle state currently inline in `IssueDetailPage`:

| Current inline code | Hook field |
|---|---|
| `createTerminal`, `killTerminal` mutations | `createTerminal`, `killTerminal` |
| `terminals`, `countData`, `configData` queries | `terminals`, `terminalCount`, `terminalConfig` |
| `hasAny`, `hasSplit` derived booleans | `hasAny`, `hasSplit` |
| `showLimitWarning`, `setShowLimitWarning` | `showLimitWarning`, `setShowLimitWarning` |
| `showCloseConfirm`, `setShowCloseConfirm` | `showCloseConfirm`, `setShowCloseConfirm` |
| `doOpenTerminal`, `openTerminal` functions | `openTerminal`, `openAnyway` |
| `closeAll` function | `closeAll` |
| `rightPanel`, `setRightPanel` tab state | `rightPanel`, `setRightPanel` |
| Memoized `handleDownload` | `handleDownload` (useCallback wrapping existing `handleDownload`) |
| Memoized `handleSessionEnd` (wraps `killTerminal.mutate(id)`) | `handleSessionEnd` (useCallback, satisfies acceptance criterion 4) |

Signature:
```typescript
export function useTerminalLayout(projectId: string, issueId: string) {
  // ... returns {
  //   terminals, hasAny, hasSplit, openTerminal, openAnyway,
  //   closeAll, rightPanel, setRightPanel,
  //   showLimitWarning, setShowLimitWarning, showCloseConfirm, setShowCloseConfirm,
  //   createTerminal, killTerminal, activeRun,
  //   handleSessionEnd: (id: string) => void,  // memoized via useCallback
  //   handleDownload: (id: string) => void,    // memoized via useCallback
  // }
}
```

### 2. Extract `TerminalActionBar` component
**File:** `frontend/src/features/terminals/components/terminal-action-bar.tsx`

Renders the terminal open/close button bar (lines 101-120).

Props:
```typescript
{
  hasAny: boolean;
  hasSplit: boolean;
  openTerminal: () => void;
  onRequestClose: () => void;  // triggers close confirmation dialog (setShowCloseConfirm(true)), NOT direct closeAll
  isOpening: boolean;
}
```

Key behavior detail: "Close Terminal" (hasAny && !hasSplit) and "Close All" (hasSplit) buttons both open the confirmation dialog via `onRequestClose`. The actual kill-terminals logic stays in `useTerminalLayout.closeAll` which is called by `TerminalDialogs` confirm button.

### 3. Extract `PendingQuestionsSection` component
**File:** `frontend/src/features/questions/components/pending-questions-section.tsx`

Renders the duplicated Pending Questions block (lines 128-137). Simple presentational component.

Props: `{ pendingQuestions?: PendingQuestion[] }`

### 4. Extract `Dialogs` component
**File:** `frontend/src/features/terminals/components/terminal-dialogs.tsx`

Renders both dialogs (LimitWarning + CloseConfirm). Takes all dialog state + actions from `useTerminalLayout`.

Props:
```typescript
{
  showLimitWarning: boolean;
  openAnyway: () => void;
  setShowLimitWarning: (v: boolean) => void;
  showCloseConfirm: boolean;
  closeAll: () => void;  // actual kill-terminals function, called from dialog confirm button
  setShowCloseConfirm: (v: boolean) => void;
  hasSplit: boolean;
}
```

### 5. Simplify `IssueDetailPage` render

Replace the 10-branch nested conditional tree with a computed layout approach:

```typescript
// Determine layout mode
const layoutMode = !hasAny && !activeRun ? 'issue-only'
  : !hasAny && activeRun ? 'issue-pipeline'
  : activeRun ? 'tabs-mode'    // hasTerminals + activeRun — subdivides via rightPanel tab (terminal/pipeline) and hasSplit (single/split)
  : 'single-terminal';         // hasTerminals, no activeRun
```

Then render once per layout mode — no duplicated blocks. Each mode renders exactly one `PendingQuestionsSection` and appropriate terminal content.

Key structure:
- Left panel (IssueDetail + PendingQuestionsSection) always rendered the same way via its own extracted sub-block or inline — single render point, not 3x duplicated
- Right panel (terminals/pipeline) rendered based on `layoutMode` and sub-conditioned on `hasSplit` and `rightPanel`
- `ScrollArea` wrappers per mode as appropriate — the left-content always scrolls; right-panel non-terminal content scrolls; terminal content gets its own scroll via xterm

### 6. Memoize callbacks

Memoized via `useCallback` inside `useTerminalLayout`:
```typescript
const handleSessionEnd = useCallback((id: string) => killTerminal.mutate(id), [killTerminal]);
const handleDownload = useCallback((id: string) => window.open(`/api/terminals/${id}/recording`), []);
```

These are returned from the hook and passed to each `TerminalWithQuestions` instance, replacing the current inline arrow functions.

### 7. Single ErrorBoundary

Replace 4 per-branch `ErrorBoundary` wrappers with a single wrapper wrapping the main content rendering (after loading/not-found guards):

```typescript
// loading state — no ErrorBoundary needed
if (isLoading) return <Skeleton />;
if (!issue) return <NotFound />;

return (
  <div className="h-[calc(100vh-1rem)] flex flex-col">
    <TerminalActionBar ... />
    <ErrorBoundary>
      {layoutContent}  {/* single rendering point for all layout modes */}
    </ErrorBoundary>
    <TerminalDialogs ... />
  </div>
);
```

## Acceptance Criteria

1. `IssueDetailPage` reduced from 324 lines to ~80-100 lines
2. Zero duplicated JSX blocks
3. All 4 ErrorBoundary instances replaced by 1
4. All callback props use `useCallback` (via `useTerminalLayout` returning `handleSessionEnd` and `handleDownload`)
5. All existing terminal behaviors preserved: open, close, split, close-all, limit warning, pipeline toggle
6. All existing `hideQuestions` behavior preserved (questions only in left panel)
7. No test failures

## Constraints

- Follow existing codebase naming conventions (kebab-case filenames, PascalCase components, camelCase hooks)
- New files go in existing feature directories, no new top-level folders
- No external dependencies added
- No CSS changes
