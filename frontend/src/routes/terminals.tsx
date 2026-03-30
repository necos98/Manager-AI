import { createFileRoute } from "@tanstack/react-router";
import { useTerminals, useTerminalConfig, useKillTerminal } from "@/features/terminals/hooks";
import { TerminalGrid } from "@/features/terminals/components/terminal-grid";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/terminals")({
  component: TerminalsPage,
});

function TerminalsPage() {
  const { data: terminals, isLoading } = useTerminals();
  const { data: config } = useTerminalConfig();
  const killTerminal = useKillTerminal();
  const softLimit = config?.soft_limit ?? 5;

  const handleKill = (terminalId: string) => {
    if (!confirm("Terminare questo terminale? I comandi in esecuzione verranno interrotti.")) return;
    killTerminal.mutate(terminalId);
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
    </div>
  );
}
