# Implementation Plan: Refactor `$issueId.tsx` Monolith Into Focused Components

## Overview

Decompose `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` (324 lines, 1 monolithic `IssueDetailPage` component) into focused parts: 1 custom hook + 3 components. Target: reduce main component to ~80-100 lines, zero duplicated JSX, single ErrorBoundary, memoized callbacks.

## Files Changed

| File | Operation | Lines |
|------|-----------|-------|
| `frontend/src/features/terminals/hooks.ts` | Add `useTerminalLayout` hook | +~70 |
| `frontend/src/features/issues/components/pending-questions-section.tsx` | **New** — PendingQuestionsSection | +~20 |
| `frontend/src/features/terminals/components/terminal-action-bar.tsx` | **New** — TerminalActionBar | +~35 |
| `frontend/src/features/terminals/components/terminal-dialogs.tsx` | **New** — TerminalDialogs | +~65 |
| `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` | Simplify IssueDetailPage | 324→~90 |

## Step 1: Add `useTerminalLayout` hook to `hooks.ts`

**File:** `frontend/src/features/terminals/hooks.ts`

Add `import { useCallback, useState } from "react";` at top of file (hooks.ts currently imports only from @tanstack/react-query and ./api).

Add new export after `useTerminalCommandTemplates` at line 183. Hook signature:

```typescript
export function useTerminalLayout(projectId: string, issueId: string) {
  // Queries — reuse existing hooks from this file + pipeline-runs/hooks
  const { data: terminals } = useTerminals(undefined, issueId);
  const createTerminal = useCreateTerminal();
  const killTerminal = useKillTerminal();
  const { data: countData } = useTerminalCount();
  const { data: configData } = useTerminalConfig();
  const { data: pipelineRuns } = usePipelineRuns(projectId, issueId, { refetchInterval: 3000 });

  // Derived
  const activeRun = pipelineRuns?.find((r) => r.status === "RUNNING") ?? null;
  const terminal1 = terminals?.[0] ?? null;
  const terminal2 = terminals?.[1] ?? null;
  const hasAny = !!terminal1;
  const hasSplit = !!terminal2;

  // State
  const [showLimitWarning, setShowLimitWarning] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [rightPanel, setRightPanel] = useState<"terminal" | "pipeline">("terminal");

  // Handlers
  const doOpenTerminal = useCallback(async () => {
    setShowLimitWarning(false);
    try {
      await createTerminal.mutateAsync({ issue_id: issueId, project_id: projectId, run_commands: false });
    } catch (err) {
      toast.error("Failed to open terminal: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  }, [createTerminal, issueId, projectId]);

  const openTerminal = useCallback(async () => {
    const count = countData?.count ?? 0;
    const softLimit = configData?.soft_limit ?? 5;
    if (count >= softLimit) { setShowLimitWarning(true); return; }
    await doOpenTerminal();
  }, [countData, configData, doOpenTerminal]);

  const closeAll = useCallback(async () => {
    setShowCloseConfirm(false);
    for (const t of terminals ?? []) {
      try { await killTerminal.mutateAsync(t.id); } catch { /* already dead */ }
    }
  }, [terminals, killTerminal]);

  const handleSessionEnd = useCallback((id: string) => killTerminal.mutate(id), [killTerminal]);
  const handleDownload = useCallback((id: string) => { window.open(`/api/terminals/${id}/recording`); }, []);

  // Layout mode — computed from state
  const layoutMode: 'issue-only' | 'issue-pipeline' | 'tabs-mode' | 'single-terminal' = !hasAny && !activeRun ? 'issue-only'
    : !hasAny && activeRun ? 'issue-pipeline'
    : activeRun ? 'tabs-mode'
    : 'single-terminal';

  return {
    terminals, terminal1, terminal2, hasAny, hasSplit,
    activeRun, layoutMode, createTerminal, killTerminal,
    openTerminal, doOpenTerminal, closeAll,
    showLimitWarning, setShowLimitWarning,
    showCloseConfirm, setShowCloseConfirm,
    rightPanel, setRightPanel,
    handleSessionEnd, handleDownload,
    isOpening: createTerminal.isPending,
  };
}
```

**Key details:**
- Import `useCallback`, `useState` from React (hooks.ts doesn't import React hooks yet — add at top of file)
- Import `usePipelineRuns` from `@/features/pipeline-runs/hooks` (cross-feature import, no circular dep since pipeline-runs doesn't import from terminals)
- Import `toast` from `sonner` (already imported in hooks.ts at line 2)
- Handler bodies copied from IssueDetailPage lines 59-84 exactly (no behavior change)
- `layoutMode` computed from same conditions as current nested if-else tree

## Step 2: Create `PendingQuestionsSection` component

**New file:** `frontend/src/features/questions/components/pending-questions-section.tsx`

```tsx
import { QuestionCard } from "./question-card";
import type { Question } from "@/shared/types";

interface PendingQuestionsSectionProps {
  pendingQuestions?: Question[];
}

export function PendingQuestionsSection({ pendingQuestions }: PendingQuestionsSectionProps) {
  if (!pendingQuestions || pendingQuestions.length === 0) return null;
  return (
    <div className="border-t mt-6 pt-6 px-4">
      <h3 className="text-sm font-medium mb-3">Pending Questions</h3>
      <div className="space-y-3">
        {pendingQuestions.map((q) => (
          <QuestionCard key={q.id} question={q} />
        ))}
      </div>
    </div>
  );
}
```

Pure presentational component. Renders nothing when empty/null — same behavior as current `&&` guard in IssueDetailPage. Type is `Question` from `@/shared/types` (the same type `usePendingQuestions` returns — no separate `PendingQuestion` type exists).

## Step 3: Create `TerminalActionBar` component

**New file:** `frontend/src/features/terminals/components/terminal-action-bar.tsx`

```tsx
import { Play, Square } from "lucide-react";
import { Button } from "@/shared/components/ui/button";

interface TerminalActionBarProps {
  hasAny: boolean;
  hasSplit: boolean;
  openTerminal: () => void;
  onRequestClose: () => void;
  isOpening: boolean;
}

export function TerminalActionBar({ hasAny, hasSplit, openTerminal, onRequestClose, isOpening }: TerminalActionBarProps) {
  return (
    <div className="flex items-center justify-end gap-2 px-6 py-2 border-b flex-shrink-0">
      {!hasAny && (
        <Button size="sm" onClick={openTerminal} disabled={isOpening}>
          <Play className="size-3 mr-1" />
          {isOpening ? "Opening..." : "Open Terminal"}
        </Button>
      )}
      {hasAny && !hasSplit && (
        <Button variant="destructive" size="sm" onClick={onRequestClose}>
          <Square className="size-3 mr-1" />
          Close Terminal
        </Button>
      )}
      {hasSplit && (
        <Button variant="destructive" size="sm" onClick={onRequestClose}>
          <Square className="size-3 mr-1" />
          Close All
        </Button>
      )}
    </div>
  );
}
```

**Key boundary rule:** Buttons call `onRequestClose` (which triggers `setShowCloseConfirm(true)`), NOT `closeAll` directly. Actual kill happens in TerminalDialogs confirm button.

## Step 4: Create `TerminalDialogs` component

**New file:** `frontend/src/features/terminals/components/terminal-dialogs.tsx`

```tsx
import { Button } from "@/shared/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/shared/components/ui/dialog";

interface TerminalDialogsProps {
  showLimitWarning: boolean;
  setShowLimitWarning: (v: boolean) => void;
  openAnyway: () => void;
  showCloseConfirm: boolean;
  setShowCloseConfirm: (v: boolean) => void;
  closeAll: () => void;
  hasSplit: boolean;
}

export function TerminalDialogs({
  showLimitWarning, setShowLimitWarning, openAnyway,
  showCloseConfirm, setShowCloseConfirm, closeAll, hasSplit,
}: TerminalDialogsProps) {
  return (
    <>
      <Dialog open={showLimitWarning} onOpenChange={setShowLimitWarning}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Terminal Limit Reached</DialogTitle>
            <DialogDescription>
              You have reached the soft limit of open terminals. Consider closing unused terminals.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLimitWarning(false)}>Cancel</Button>
            <Button onClick={openAnyway}>Open Anyway</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Close Terminal{hasSplit ? "s" : ""}?</DialogTitle>
            <DialogDescription>
              This will kill the terminal process{hasSplit ? "es" : ""}. Any running commands will be terminated.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCloseConfirm(false)}>Cancel</Button>
            <Button variant="destructive" onClick={closeAll}>
              Close {hasSplit ? "All" : "Terminal"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

Props driven entirely from `useTerminalLayout` return values (`doOpenTerminal` maps to `openAnyway` prop). No internal state.

## Step 5: Simplify `IssueDetailPage` in `$issueId.tsx`

Cut from 324 lines to ~90. New structure:

### Imports (reduced)
- Remove: `useState`, `Play`, `Square`, `QuestionCard`, `Button`, `Dialog*`, `Resizable*`, `ScrollArea`, `Tabs*` (moved to extracted files/components)
- Keep: `useEffect`, `createFileRoute`, `useIssue`, `useProject`, `usePendingQuestions`, `Skeleton`
- Add imports: `useTerminalLayout` from features/terminals/hooks, all 3 new components
- Import `ErrorBoundary` from shared components (still needed for single top-level wrapper)

### Component body

```tsx
function IssueDetailPage() {
  const { projectId, issueId } = Route.useParams();
  const { data: project } = useProject(projectId);
  const { data: issue, isLoading } = useIssue(projectId, issueId);
  const { data: pendingQuestions } = usePendingQuestions(projectId, issueId);
  const layout = useTerminalLayout(projectId, issueId);

  useEffect(() => {
    const issueName = issue?.name || issue?.description;
    if (issueName && project) document.title = `${issueName} - ${project.name}`;
    else if (issueName) document.title = issueName;
  }, [issue, project]);

  // Loading / not-found guards
  if (isLoading) return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-32" />
      <Skeleton className="h-48" />
    </div>
  );
  if (!issue) return <div className="p-6"><p className="text-destructive">Issue not found.</p></div>;

  // Render — single ErrorBoundary wrapping all layout modes
  return (
    <div className="h-[calc(100vh-1rem)] flex flex-col">
      <TerminalActionBar
        hasAny={layout.hasAny}
        hasSplit={layout.hasSplit}
        openTerminal={layout.openTerminal}
        onRequestClose={() => layout.setShowCloseConfirm(true)}
        isOpening={layout.isOpening}
      />
      <ErrorBoundary>
        <LayoutContent layout={layout} issue={issue} pendingQuestions={pendingQuestions} projectId={projectId} />
      </ErrorBoundary>
      <TerminalDialogs
        showLimitWarning={layout.showLimitWarning}
        setShowLimitWarning={layout.setShowLimitWarning}
        openAnyway={layout.doOpenTerminal}
        showCloseConfirm={layout.showCloseConfirm}
        setShowCloseConfirm={layout.setShowCloseConfirm}
        closeAll={layout.closeAll}
        hasSplit={layout.hasSplit}
      />
    </div>
  );
}
```

### LayoutContent sub-component (in same file, only IssueDetailPage uses it)

```tsx
function LayoutContent({
  layout, issue, pendingQuestions, projectId,
}: {
  layout: ReturnType<typeof useTerminalLayout>;
  issue: Issue;
  pendingQuestions: Question[] | undefined;
  projectId: string;
}) {
  // Left panel content shared by all modes
  const leftPanel = (
    <>
      <IssueDetail issue={issue} projectId={projectId} terminalId={layout.terminal1?.id ?? null} />
      <PendingQuestionsSection pendingQuestions={pendingQuestions} />
    </>
  );

  // Right panel: terminal(s) render helper
  const terminalPanel = (terminal: typeof layout.terminal1) =>
    terminal && (
      <TerminalWithQuestions
        key={terminal.id}
        terminalId={terminal.id}
        projectId={projectId}
        issueId={terminal.issue_id}
        hideQuestions
        onSessionEnd={layout.handleSessionEnd}
        onDownloadRecording={layout.handleDownload}
      />
    );

  const splitTerminals = (t1: typeof layout.terminal1, t2: typeof layout.terminal2) => (
    <ResizablePanelGroup direction="vertical">
      <ResizablePanel defaultSize={50} minSize={20}>
        {terminalPanel(t1)}
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={50} minSize={20}>
        {terminalPanel(t2)}
      </ResizablePanel>
    </ResizablePanelGroup>
  );

  // Render based on layout mode
  const rightContent = layout.layoutMode === 'issue-only' ? null
    : layout.layoutMode === 'issue-pipeline' ? (
      <div className="border-t h-[400px]">
        <PipelineProgress projectId={projectId} issueId={issueId} />
      </div>
    ) : layout.layoutMode === 'tabs-mode' ? (
      <Tabs value={layout.rightPanel} onValueChange={(v) => layout.setRightPanel(v as "terminal" | "pipeline")} className="h-full flex flex-col">
        <TabsList className="mx-2 mt-1 shrink-0">
          <TabsTrigger value="terminal" className="text-xs">Terminal</TabsTrigger>
          <TabsTrigger value="pipeline" className="text-xs">Pipeline</TabsTrigger>
        </TabsList>
        <div className="flex-1 min-h-0">
          {layout.rightPanel === "terminal"
            ? layout.hasSplit
              ? splitTerminals(layout.terminal1, layout.terminal2)
              : terminalPanel(layout.terminal1)
            : <PipelineProgress projectId={projectId} issueId={issueId} />
          }
        </div>
      </Tabs>
    ) : ( /* single-terminal */
      layout.hasSplit
        ? splitTerminals(layout.terminal1, layout.terminal2)
        : terminalPanel(layout.terminal1)
    );

  if (layout.layoutMode === 'issue-only') {
    return <ScrollArea className="flex-1">{leftPanel}</ScrollArea>;
  }

  if (layout.layoutMode === 'issue-pipeline') {
    return (
      <ScrollArea className="flex-1">
        {leftPanel}
        {rightContent}
      </ScrollArea>
    );
  }

  // Has terminals — split view with terminal in right panel
  return (
    <ResizablePanelGroup direction="horizontal" className="flex-1 min-h-0">
      <ResizablePanel defaultSize={55} minSize={30}>
        <ScrollArea className="h-full">{leftPanel}</ScrollArea>
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={45} minSize={20}>
        {rightContent}
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
```

Note: `Issue` type imported from `@/shared/types`. `PendingQuestionsSection` uses `Question[]` type (not `PendingQuestion` — that type doesn't exist; `usePendingQuestions` returns `Question[]`).

### Key details
- `ScrollArea` used only for scrollable content (left panel)
- `ResizablePanelGroup` only for split modes
- `Tabs` with `TabsList`/`TabsTrigger` only in `tabs-mode`
- `PipelineProgress` only in `issue-pipeline` (no terminal) and `tabs-mode.pipeline` tab
- `TerminalWithQuestions` gets `handleSessionEnd` and `handleDownload` from layout hook (memoized via useCallback)
- Inline arrow functions eliminated from all TerminalWithQuestions props
- Loading/not-found states escape without ErrorBoundary (intentional — skeleton errors shouldn't be masked)
- Use same inline skeleton and not-found rendering as current code (no separate SkeletonPage/NotFound components needed)

## Step 6: Single ErrorBoundary (already covered in Step 5)

Current: 4 ErrorBoundary instances (lines 126, 143, 165, and implicit in each branch). New: 1 `<ErrorBoundary>` wrapping `LayoutContent`. Loading/not-found states escape without ErrorBoundary.

## Dependencies

- `usePipelineRuns` from `@/features/pipeline-runs/hooks` — used inside `hooks.ts` (cross-feature import; verified no circular deps exist)
- `Question` type from `@/shared/types` — used by PendingQuestionsSection
- All new components use existing shadcn/ui imports already present in codebase

## No-Go Areas

- Zero changes to backend
- Zero changes to `TerminalWithQuestions`, `TerminalPanel`, `PipelineProgress`, `IssueDetail`, `QuestionCard`
- Zero CSS changes
- Zero new dependencies
- Zero test additions

## Build Order

1. `hooks.ts` — add `useTerminalLayout` (foundation that new components depend on)
2. `PendingQuestionsSection` — simple, no dependencies on other new code
3. `TerminalActionBar` — depends on hook fields
4. `TerminalDialogs` — depends on hook fields
5. `$issueId.tsx` — final integration, depends on all above