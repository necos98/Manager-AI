import { useState } from "react";
import { PlayCircle, CheckCircle, XCircle, Loader2 } from "lucide-react";
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
  useStartAnalysis,
  useAcceptIssue,
  useCancelIssue,
  useCompleteIssue,
} from "@/features/issues/hooks";
import type { Issue } from "@/shared/types";

interface IssueActionsProps {
  issue: Issue;
  projectId: string;
}

type ActionType = "start-analysis" | "accept" | "cancel" | "complete";

const CONFIRM_COPY: Record<ActionType, { title: string; description: string; confirm: string }> = {
  "start-analysis": {
    title: "Avvia Analisi",
    description: "Claude analizzerà la descrizione e scriverà spec, piano e task. Questo potrebbe richiedere qualche minuto.",
    confirm: "Avvia",
  },
  accept: {
    title: "Accetta Piano",
    description: "Accettare il piano trasferisce l'issue in stato Accepted e avvia il workflow di implementazione.",
    confirm: "Accetta",
  },
  cancel: {
    title: "Cancella Issue",
    description: "Questa azione non può essere annullata. L'issue verrà marcata come Canceled.",
    confirm: "Cancella",
  },
  complete: {
    title: "Segna come Completata",
    description: "Tutti i task devono essere completati. Inserisci un recap di cosa è stato fatto.",
    confirm: "Completa",
  },
};

export function IssueActions({ issue, projectId }: IssueActionsProps) {
  const [confirmAction, setConfirmAction] = useState<ActionType | null>(null);
  const [recap, setRecap] = useState("");

  const startAnalysis = useStartAnalysis(projectId, issue.id);
  const acceptIssue = useAcceptIssue(projectId, issue.id);
  const cancelIssue = useCancelIssue(projectId, issue.id);
  const completeIssue = useCompleteIssue(projectId, issue.id);

  const isPending =
    startAnalysis.isPending ||
    acceptIssue.isPending ||
    cancelIssue.isPending ||
    completeIssue.isPending;

  const handleConfirm = () => {
    if (confirmAction === "start-analysis") {
      startAnalysis.mutate(undefined, { onSuccess: () => setConfirmAction(null) });
    } else if (confirmAction === "accept") {
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
        {issue.status === "New" && (
          <Button size="sm" onClick={() => setConfirmAction("start-analysis")} disabled={isPending}>
            <PlayCircle className="size-4 mr-1" />
            Avvia Analisi
          </Button>
        )}
        {issue.status === "Planned" && (
          <Button size="sm" onClick={() => setConfirmAction("accept")} disabled={isPending}>
            <CheckCircle className="size-4 mr-1" />
            Accetta Piano
          </Button>
        )}
        {issue.status === "Accepted" && (
          <Button size="sm" onClick={() => setConfirmAction("complete")} disabled={isPending}>
            <CheckCircle className="size-4 mr-1" />
            Segna come Completata
          </Button>
        )}
        <Button
          size="sm"
          variant="outline"
          className="text-destructive hover:text-destructive"
          onClick={() => setConfirmAction("cancel")}
          disabled={isPending}
        >
          <XCircle className="size-4 mr-1" />
          Cancella Issue
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
              <Textarea
                placeholder="Descrivi cosa è stato implementato..."
                value={recap}
                onChange={(e) => setRecap(e.target.value)}
                rows={4}
                className="mt-2"
              />
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmAction(null)}>
                Annulla
              </Button>
              <Button
                variant={confirmAction === "cancel" ? "destructive" : "default"}
                onClick={handleConfirm}
                disabled={isPending || (confirmAction === "complete" && !recap.trim())}
              >
                {isPending ? <Loader2 className="size-4 mr-1 animate-spin" /> : null}
                {isPending ? "In corso..." : copy.confirm}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
