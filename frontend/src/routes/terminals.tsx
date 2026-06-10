import { createFileRoute } from "@tanstack/react-router";
import { useTerminals, useTerminalConfig, useKillTerminal } from "@/features/terminals/hooks";
import { TerminalGrid } from "@/features/terminals/components/terminal-grid";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Button } from "@/shared/components/ui/button";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";

export const Route = createFileRoute("/terminals")({
  component: TerminalsPage,
});

function TerminalsPage() {
  const { data: terminals, isLoading } = useTerminals();
  const { data: config } = useTerminalConfig();
  const killTerminal = useKillTerminal();
  const softLimit = config?.soft_limit ?? 5;
  const [confirmKillId, setConfirmKillId] = useState<string | null>(null);

  const handleKill = (terminalId: string) => {
    setConfirmKillId(terminalId);
  };

  const doKill = () => {
    if (!confirmKillId) return;
    killTerminal.mutate(confirmKillId, {
      onSuccess: () => setConfirmKillId(null),
    });
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-48" />
        {[1, 2].map((i) => <Skeleton key={i} className="h-[400px]" />)}
      </div>
    );
  }

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <h1 className="text-xl font-semibold">Terminali Attivi</h1>
        <span className="text-sm text-muted-foreground">
          {terminals?.length ?? 0} / {softLimit} (soft limit)
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <TerminalGrid terminals={terminals ?? []} onKill={handleKill} />
      </div>

      {/* Kill confirmation */}
      <Dialog open={confirmKillId !== null} onOpenChange={() => setConfirmKillId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Terminate Terminal?</DialogTitle>
            <DialogDescription>
              Terminare questo terminale? I comandi in esecuzione verranno interrotti.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmKillId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={doKill}
              disabled={killTerminal.isPending}
            >
              {killTerminal.isPending ? "Terminating..." : "Terminate"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
