import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Play, Square } from "lucide-react";
import { toast } from "sonner";
import { useIssue } from "@/features/issues/hooks";
import { useProject } from "@/features/projects/hooks";
import { useTerminals, useCreateTerminal, useKillTerminal, useTerminalCount, useTerminalConfig } from "@/features/terminals/hooks";
import { usePipelineRuns } from "@/features/pipeline-runs/hooks";
import { PipelineProgress } from "@/features/pipeline-runs/components/PipelineProgress";
import { IssueDetail } from "@/features/issues/components/issue-detail";
import { TerminalWithQuestions } from "@/features/terminals/components/terminal-with-questions";
import { ErrorBoundary } from "@/shared/components/error-boundary";
import { usePendingQuestions } from "@/features/questions/hooks";
import { QuestionCard } from "@/features/questions/components/question-card";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  ResizableHandle, ResizablePanel, ResizablePanelGroup,
} from "@/shared/components/ui/resizable";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";

export const Route = createFileRoute("/projects/$projectId/issues/$issueId")({
  component: IssueDetailPage,
});

function IssueDetailPage() {
  const { projectId, issueId } = Route.useParams();
  const { data: project } = useProject(projectId);
  const { data: issue, isLoading } = useIssue(projectId, issueId);

  useEffect(() => {
    const issueName = issue?.name || issue?.description;
    if (issueName && project) document.title = `${issueName} - ${project.name}`;
    else if (issueName) document.title = issueName;
  }, [issue, project]);

  const { data: terminals } = useTerminals(undefined, issueId);
  const createTerminal = useCreateTerminal();
  const killTerminal = useKillTerminal();
  const { data: countData } = useTerminalCount();
  const { data: configData } = useTerminalConfig();
  const { data: pendingQuestions } = usePendingQuestions(projectId, issueId);
  const [showLimitWarning, setShowLimitWarning] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);

  const { data: pipelineRuns } = usePipelineRuns(projectId, issueId, { refetchInterval: 3000 });
  const activeRun = pipelineRuns?.find((r) => r.status === "RUNNING") ?? null;

  const terminal1 = terminals?.[0] ?? null;
  const terminal2 = terminals?.[1] ?? null;
  const hasAny = !!terminal1;
  const hasSplit = !!terminal2;
  const [rightPanel, setRightPanel] = useState<"terminal" | "pipeline">("terminal");

  const handleDownload = (terminalId: string) => {
    window.open(`/api/terminals/${terminalId}/recording`);
  };

  const doOpenTerminal = async () => {
    setShowLimitWarning(false);
    try {
      await createTerminal.mutateAsync({ issue_id: issueId, project_id: projectId, run_commands: false });
    } catch (err) {
      toast.error("Failed to open terminal: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  };

  const openTerminal = async () => {
    const count = countData?.count ?? 0;
    const softLimit = configData?.soft_limit ?? 5;
    if (count >= softLimit) { setShowLimitWarning(true); return; }
    await doOpenTerminal();
  };

  const closeAll = async () => {
    setShowCloseConfirm(false);
    for (const t of terminals ?? []) {
      try { await killTerminal.mutateAsync(t.id); } catch { /* already dead */ }
    }
  };

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
      {/* Terminal action bar */}
      <div className="flex items-center justify-end gap-2 px-6 py-2 border-b flex-shrink-0">
        {!hasAny && (
          <Button size="sm" onClick={openTerminal} disabled={createTerminal.isPending}>
            <Play className="size-3 mr-1" />
            {createTerminal.isPending ? "Opening..." : "Open Terminal"}
          </Button>
        )}
        {hasAny && !hasSplit && (
          <Button variant="destructive" size="sm" onClick={() => setShowCloseConfirm(true)}>
            <Square className="size-3 mr-1" />
            Close Terminal
          </Button>
        )}
        {hasSplit && (
          <Button variant="destructive" size="sm" onClick={() => setShowCloseConfirm(true)}>
            <Square className="size-3 mr-1" />
            Close All
          </Button>
        )}
      </div>

      {/* Right panel content: terminal, pipeline progress, or both togglable */}
      {!hasAny && !activeRun ? (
        /* No terminal, no pipeline: full-width issue detail */
        <ScrollArea className="flex-1">
          <ErrorBoundary>
            <IssueDetail issue={issue} projectId={projectId} terminalId={null} />
            {pendingQuestions && pendingQuestions.length > 0 && (
              <div className="border-t mt-6 pt-6 px-4">
                <h3 className="text-sm font-medium mb-3">Pending Questions</h3>
                <div className="space-y-3">
                  {pendingQuestions.map((q) => (
                    <QuestionCard key={q.id} question={q} />
                  ))}
                </div>
              </div>
            )}
          </ErrorBoundary>
        </ScrollArea>
      ) : !hasAny && activeRun ? (
        /* Pipeline progress only, no terminal */
        <ScrollArea className="flex-1">
          <ErrorBoundary>
            <IssueDetail issue={issue} projectId={projectId} terminalId={null} />
            {pendingQuestions && pendingQuestions.length > 0 && (
              <div className="border-t mt-6 pt-6 px-4">
                <h3 className="text-sm font-medium mb-3">Pending Questions</h3>
                <div className="space-y-3">
                  {pendingQuestions.map((q) => (
                    <QuestionCard key={q.id} question={q} />
                  ))}
                </div>
              </div>
            )}
          </ErrorBoundary>
          <div className="border-t h-[400px]">
            <PipelineProgress projectId={projectId} issueId={issueId} />
          </div>
        </ScrollArea>
      ) : (
        /* Has terminal (and possibly pipeline): split view */
        <ResizablePanelGroup direction="horizontal" className="flex-1 min-h-0">
          <ResizablePanel defaultSize={55} minSize={30}>
            <ScrollArea className="h-full">
              <ErrorBoundary>
                <IssueDetail issue={issue} projectId={projectId} terminalId={terminal1?.id ?? null} />
                {pendingQuestions && pendingQuestions.length > 0 && (
                  <div className="border-t mt-6 pt-6 px-4">
                    <h3 className="text-sm font-medium mb-3">Pending Questions</h3>
                    <div className="space-y-3">
                      {pendingQuestions.map((q) => (
                        <QuestionCard key={q.id} question={q} />
                      ))}
                    </div>
                  </div>
                )}
              </ErrorBoundary>
            </ScrollArea>
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={45} minSize={20}>
            {/* Toggle between terminal and pipeline when both exist */}
            {activeRun && (
              <Tabs value={rightPanel} onValueChange={(v) => setRightPanel(v as "terminal" | "pipeline")} className="h-full flex flex-col">
                <TabsList className="mx-2 mt-1 shrink-0">
                  <TabsTrigger value="terminal" className="text-xs">Terminal</TabsTrigger>
                  <TabsTrigger value="pipeline" className="text-xs">Pipeline</TabsTrigger>
                </TabsList>
                <div className="flex-1 min-h-0">
                  {rightPanel === "terminal" ? (
                    !hasSplit ? (
                      terminal1 && (
                        <TerminalWithQuestions
                          terminalId={terminal1.id}
                          projectId={projectId}
                          issueId={terminal1.issue_id}
                          onSessionEnd={() => killTerminal.mutate(terminal1.id)}
                          onDownloadRecording={() => handleDownload(terminal1.id)}
                        />
                      )
                    ) : (
                      <ResizablePanelGroup direction="vertical">
                        <ResizablePanel defaultSize={50} minSize={20}>
                          {terminal1 && (
                            <TerminalWithQuestions
                              terminalId={terminal1.id}
                              projectId={projectId}
                              issueId={terminal1.issue_id}
                              onSessionEnd={() => killTerminal.mutate(terminal1.id)}
                              onDownloadRecording={() => handleDownload(terminal1.id)}
                            />
                          )}
                        </ResizablePanel>
                        <ResizableHandle withHandle />
                        <ResizablePanel defaultSize={50} minSize={20}>
                          {terminal2 && (
                            <TerminalWithQuestions
                              terminalId={terminal2.id}
                              projectId={projectId}
                              issueId={terminal2.issue_id}
                              onSessionEnd={() => killTerminal.mutate(terminal2.id)}
                              onDownloadRecording={() => handleDownload(terminal2.id)}
                            />
                          )}
                        </ResizablePanel>
                      </ResizablePanelGroup>
                    )
                  ) : (
                    <PipelineProgress projectId={projectId} issueId={issueId} />
                  )}
                </div>
              </Tabs>
            )}
            {!activeRun && (
              !hasSplit ? (
                terminal1 && (
                  <TerminalWithQuestions
                    terminalId={terminal1.id}
                    projectId={projectId}
                    issueId={terminal1.issue_id}
                    onSessionEnd={() => killTerminal.mutate(terminal1.id)}
                    onDownloadRecording={() => handleDownload(terminal1.id)}
                  />
                )
              ) : (
                <ResizablePanelGroup direction="vertical">
                  <ResizablePanel defaultSize={50} minSize={20}>
                    {terminal1 && (
                      <TerminalWithQuestions
                        terminalId={terminal1.id}
                        projectId={projectId}
                        issueId={terminal1.issue_id}
                        onSessionEnd={() => killTerminal.mutate(terminal1.id)}
                        onDownloadRecording={() => handleDownload(terminal1.id)}
                      />
                    )}
                  </ResizablePanel>
                  <ResizableHandle withHandle />
                  <ResizablePanel defaultSize={50} minSize={20}>
                    {terminal2 && (
                      <TerminalWithQuestions
                        terminalId={terminal2.id}
                        projectId={projectId}
                        issueId={terminal2.issue_id}
                        onSessionEnd={() => killTerminal.mutate(terminal2.id)}
                        onDownloadRecording={() => handleDownload(terminal2.id)}
                      />
                    )}
                  </ResizablePanel>
                </ResizablePanelGroup>
              )
            )}
          </ResizablePanel>
        </ResizablePanelGroup>
      )}

      {/* Limit warning */}
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
            <Button onClick={doOpenTerminal}>Open Anyway</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Close confirmation */}
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
    </div>
  );
}
