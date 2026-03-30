import { useState } from "react";
import { CheckCircle, XCircle, Loader2, Play } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  useAcceptIssue,
  useCancelIssue,
  useCompleteIssue,
} from "@/features/issues/hooks";
import { useCreateTerminal } from "@/features/terminals/hooks";
import type { Issue } from "@/shared/types";

interface IssueActionsProps {
  issue: Issue;
  projectId: string;
}

type ActionType = "accept" | "cancel" | "complete";

const CONFIRM_COPY: Record<ActionType, { title: string; description: string; confirm: string }> = {
  accept: {
    title: "Accept Plan",
    description: "Accepting the plan moves the issue to Accepted status and starts the implementation workflow.",
    confirm: "Accept",
  },
  cancel: {
    title: "Cancel Issue",
    description: "This action cannot be undone. The issue will be marked as Canceled.",
    confirm: "Cancel",
  },
  complete: {
    title: "Mark as Complete",
    description: "All tasks must be completed. Enter a recap of what was done.",
    confirm: "Complete",
  },
};

export function IssueActions({ issue, projectId }: IssueActionsProps) {
  const [confirmAction, setConfirmAction] = useState<ActionType | null>(null);
  const [recap, setRecap] = useState("");

  const acceptIssue = useAcceptIssue(projectId, issue.id);
  const cancelIssue = useCancelIssue(projectId, issue.id);
  const completeIssue = useCompleteIssue(projectId, issue.id);

  const isPending =
    acceptIssue.isPending ||
    cancelIssue.isPending ||
    completeIssue.isPending;

  const createTerminal = useCreateTerminal();

  const handleRunIssue = () => {
    createTerminal.mutate({ issue_id: issue.id, project_id: projectId });
  };

  const handleConfirm = () => {
    if (confirmAction === "accept") {
      acceptIssue.mutate(undefined, { onSuccess: () => setConfirmAction(null) });
    } else if (confirmAction === "cancel") {
      cancelIssue.mutate(undefined, { onSuccess: () => setConfirmAction(null) });
    } else if (confirmAction === "complete") {
      completeIssue.mutate(
        { recap },
        { onSuccess: () => { setConfirmAction(null); setRecap(""); } }
      );
    }
  };

  const isTerminalState = issue.status === "Finished" || issue.status === "Canceled";
  if (isTerminalState) return null;

  const copy = confirmAction ? CONFIRM_COPY[confirmAction] : null;

  return (
    <>
      <div className="flex items-center gap-2 flex-wrap">
        {issue.status === "Planned" && (
          <Button size="sm" onClick={() => setConfirmAction("accept")} disabled={isPending}>
            <CheckCircle className="size-4 mr-1" />
            Accept Plan
          </Button>
        )}
        {issue.status === "Accepted" && (
          <Button size="sm" onClick={() => setConfirmAction("complete")} disabled={isPending}>
            <CheckCircle className="size-4 mr-1" />
            Mark as Complete
          </Button>
        )}
        <Button
          size="sm"
          variant="outline"
          onClick={handleRunIssue}
          disabled={isPending || createTerminal.isPending}
        >
          <Play className="size-4 mr-1" />
          {createTerminal.isPending ? "Opening..." : "Run Issue"}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="text-destructive hover:text-destructive"
          onClick={() => setConfirmAction("cancel")}
          disabled={isPending}
        >
          <XCircle className="size-4 mr-1" />
          Cancel Issue
        </Button>
      </div>

      {confirmAction && copy && (
        <Dialog open onOpenChange={() => setConfirmAction(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{copy.title}</DialogTitle>
              <DialogDescription>{copy.description}</DialogDescription>
            </DialogHeader>
            {confirmAction === "complete" && (
              <>
                <Textarea
                  placeholder="Describe what was implemented..."
                  value={recap}
                  onChange={(e) => setRecap(e.target.value)}
                  rows={4}
                  className="mt-2"
                />
                {recap.length > 50_000 && (
                  <p className="text-xs text-destructive mt-1">
                    Max 50,000 characters ({recap.length.toLocaleString()} / 50,000)
                  </p>
                )}
              </>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmAction(null)}>
                Cancel
              </Button>
              <Button
                variant={confirmAction === "cancel" ? "destructive" : "default"}
                onClick={handleConfirm}
                disabled={isPending || (confirmAction === "complete" && (!recap.trim() || recap.length > 50_000))}
              >
                {isPending ? <Loader2 className="size-4 mr-1 animate-spin" /> : null}
                {isPending ? "Working..." : copy.confirm}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
