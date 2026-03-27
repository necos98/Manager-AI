import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Play, Square } from "lucide-react";
import { toast } from "sonner";
import { useIssue } from "@/features/issues/hooks";
import { useTerminals, useCreateTerminal, useKillTerminal, useTerminalCount, useTerminalConfig } from "@/features/terminals/hooks";
import { IssueDetail } from "@/features/issues/components/issue-detail";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/shared/components/ui/resizable";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/$projectId/issues/$issueId")({
  component: IssueDetailPage,
});

function IssueDetailPage() {
  const { projectId, issueId } = Route.useParams();
  const { data: issue, isLoading } = useIssue(projectId, issueId);
  const { data: terminals } = useTerminals(undefined, issueId);
  const createTerminal = useCreateTerminal();
  const killTerminal = useKillTerminal();
  const { data: countData } = useTerminalCount();
  const { data: configData } = useTerminalConfig();
  const [showLimitWarning, setShowLimitWarning] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);

  const terminalId = terminals?.[0]?.id ?? null;

  const openTerminal = async () => {
    const count = countData?.count ?? 0;
    const softLimit = configData?.soft_limit ?? 5;
    if (count >= softLimit) {
      setShowLimitWarning(true);
      return;
    }
    await doOpenTerminal();
  };

  const doOpenTerminal = async () => {
    setShowLimitWarning(false);
    try {
      await createTerminal.mutateAsync({ issue_id: issueId, project_id: projectId });
    } catch (err) {
      toast.error("Failed to open terminal: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  };

  const closeTerminal = async () => {
    setShowCloseConfirm(false);
    if (terminalId) {
      try {
        await killTerminal.mutateAsync(terminalId);
      } catch {
        // Terminal may already be dead
      }
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

  if (!issue) {
    return (
      <div className="p-6">
        <p className="text-destructive">Issue not found.</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-1rem)] flex flex-col">
      {/* Terminal action bar */}
      <div className="flex items-center justify-end gap-2 px-6 py-2 border-b flex-shrink-0">
        {terminalId ? (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowCloseConfirm(true)}
          >
            <Square className="size-3 mr-1" />
            Close Terminal
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={openTerminal}
            disabled={createTerminal.isPending}
          >
            <Play className="size-3 mr-1" />
            {createTerminal.isPending ? "Opening..." : "Open Terminal"}
          </Button>
        )}
      </div>

      {/* Split view */}
      <ResizablePanelGroup direction="horizontal" className="flex-1 min-h-0">
        <ResizablePanel defaultSize={terminalId ? 60 : 100} minSize={30}>
          <ScrollArea className="h-full">
            <IssueDetail issue={issue} projectId={projectId} terminalId={terminalId} />
          </ScrollArea>
        </ResizablePanel>

        {terminalId && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={40} minSize={20}>
              <TerminalPanel
                terminalId={terminalId}
                onSessionEnd={() => {
                  killTerminal.mutate(terminalId);
                }}
              />
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>

      {/* Limit warning dialog */}
      <Dialog open={showLimitWarning} onOpenChange={setShowLimitWarning}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Terminal Limit Reached</DialogTitle>
            <DialogDescription>
              You have reached the soft limit of open terminals. Consider closing unused terminals to free resources.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLimitWarning(false)}>
              Cancel
            </Button>
            <Button onClick={doOpenTerminal}>Open Anyway</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Close confirmation dialog */}
      <Dialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Close Terminal?</DialogTitle>
            <DialogDescription>
              This will kill the terminal process. Any running commands will be terminated.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCloseConfirm(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={closeTerminal}>
              Close Terminal
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
