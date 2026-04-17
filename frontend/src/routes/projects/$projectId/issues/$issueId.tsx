import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Play, Square, LayoutTemplate } from "lucide-react";
import { toast } from "sonner";
import { useIssue } from "@/features/issues/hooks";
import { useProject } from "@/features/projects/hooks";
import { useTerminals, useCreateTerminal, useKillTerminal, useTerminalCount, useTerminalConfig } from "@/features/terminals/hooks";
import { IssueDetail } from "@/features/issues/components/issue-detail";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { ErrorBoundary } from "@/shared/components/error-boundary";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  ResizableHandle, ResizablePanel, ResizablePanelGroup,
} from "@/shared/components/ui/resizable";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Skeleton } from "@/shared/components/ui/skeleton";

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
  const [showLimitWarning, setShowLimitWarning] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);

  const terminal1 = terminals?.[0] ?? null;
  const terminal2 = terminals?.[1] ?? null;
  const hasAny = !!terminal1;
  const hasSplit = !!terminal2;

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
          <>
            <Button variant="outline" size="sm" onClick={openTerminal} disabled={createTerminal.isPending}>
              <LayoutTemplate className="size-3 mr-1" />
              Split
            </Button>
            <Button variant="destructive" size="sm" onClick={() => setShowCloseConfirm(true)}>
              <Square className="size-3 mr-1" />
              Close Terminal
            </Button>
          </>
        )}
        {hasSplit && (
          <Button variant="destructive" size="sm" onClick={() => setShowCloseConfirm(true)}>
            <Square className="size-3 mr-1" />
            Close All
          </Button>
        )}
      </div>

      {/* Split view */}
      {!hasAny ? (
        <ScrollArea className="flex-1">
          <ErrorBoundary>
            <IssueDetail issue={issue} projectId={projectId} terminalId={null} />
          </ErrorBoundary>
        </ScrollArea>
      ) : (
        <ResizablePanelGroup direction="horizontal" className="flex-1 min-h-0">
          <ResizablePanel defaultSize={55} minSize={30}>
            <ScrollArea className="h-full">
              <ErrorBoundary>
                <IssueDetail issue={issue} projectId={projectId} terminalId={terminal1?.id ?? null} />
              </ErrorBoundary>
            </ScrollArea>
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={45} minSize={20}>
            {!hasSplit ? (
              terminal1 && (
                <TerminalPanel
                  terminalId={terminal1.id}
                  onSessionEnd={() => killTerminal.mutate(terminal1.id)}
                  onDownloadRecording={() => handleDownload(terminal1.id)}
                />
              )
            ) : (
              <ResizablePanelGroup direction="vertical">
                <ResizablePanel defaultSize={50} minSize={20}>
                  {terminal1 && (
                    <TerminalPanel
                      terminalId={terminal1.id}
                      onSessionEnd={() => killTerminal.mutate(terminal1.id)}
                      onDownloadRecording={() => handleDownload(terminal1.id)}
                    />
                  )}
                </ResizablePanel>
                <ResizableHandle withHandle />
                <ResizablePanel defaultSize={50} minSize={20}>
                  {terminal2 && (
                    <TerminalPanel
                      terminalId={terminal2.id}
                      onSessionEnd={() => killTerminal.mutate(terminal2.id)}
                      onDownloadRecording={() => handleDownload(terminal2.id)}
                    />
                  )}
                </ResizablePanel>
              </ResizablePanelGroup>
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
