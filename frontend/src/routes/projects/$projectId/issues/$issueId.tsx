import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useIssue } from "@/features/issues/hooks";
import { useProject } from "@/features/projects/hooks";
import { useTerminalLayout } from "@/features/terminals/hooks";
import { TerminalActionBar } from "@/features/terminals/components/terminal-action-bar";
import { TerminalDialogs } from "@/features/terminals/components/terminal-dialogs";
import { PendingQuestionsSection } from "@/features/questions/components/pending-questions-section";
import { ErrorBoundary } from "@/shared/components/error-boundary";
import { usePendingQuestions } from "@/features/questions/hooks";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { IssueDetail } from "@/features/issues/components/issue-detail";
import { TerminalWithQuestions } from "@/features/terminals/components/terminal-with-questions";
import { PipelineProgress } from "@/features/pipeline-runs/components/PipelineProgress";
import {
  ResizableHandle, ResizablePanel, ResizablePanelGroup,
} from "@/shared/components/ui/resizable";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";
import type { Issue, Question } from "@/shared/types";

export const Route = createFileRoute("/projects/$projectId/issues/$issueId")({
  component: IssueDetailPage,
});

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

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (!issue) return <div className="p-6"><p className="text-destructive">Issue not found.</p></div>;

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
        <LayoutContent
          layout={layout}
          issue={issue}
          issueId={issueId}
          pendingQuestions={pendingQuestions}
          projectId={projectId}
        />
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

function LayoutContent({
  layout, issue, issueId, pendingQuestions, projectId,
}: {
  layout: ReturnType<typeof useTerminalLayout>;
  issue: Issue;
  issueId: string;
  pendingQuestions: Question[] | undefined;
  projectId: string;
}) {
  const leftPanel = (
    <>
      <IssueDetail issue={issue} projectId={projectId} terminalId={layout.terminal1?.id ?? null} />
      <PendingQuestionsSection pendingQuestions={pendingQuestions} />
    </>
  );

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
