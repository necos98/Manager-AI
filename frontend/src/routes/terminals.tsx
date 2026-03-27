import { createFileRoute, Link } from "@tanstack/react-router";
import { ExternalLink, Skull } from "lucide-react";
import { useTerminals, useTerminalConfig, useKillTerminal } from "@/features/terminals/hooks";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

function formatAge(createdAt: string): string {
  const diff = Date.now() - new Date(createdAt).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  return `${hours}h ${mins % 60}m ago`;
}

export const Route = createFileRoute("/terminals")({
  component: TerminalsPage,
});

function TerminalsPage() {
  const { data: terminals, isLoading } = useTerminals();
  const { data: config } = useTerminalConfig();
  const killTerminal = useKillTerminal();
  const softLimit = config?.soft_limit ?? 5;

  const handleKill = (terminalId: string) => {
    if (!confirm("Kill this terminal? Any running commands will be terminated.")) return;
    killTerminal.mutate(terminalId);
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-48" />
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-semibold">Active Terminals</h1>
        <span className="text-sm text-muted-foreground">
          {terminals?.length ?? 0} / {softLimit} (soft limit)
        </span>
      </div>

      {!terminals || terminals.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No active terminals.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {terminals.map((term) => (
            <div
              key={term.id}
              className="flex items-center rounded-md border px-4 py-3"
            >
              <span
                className="w-2.5 h-2.5 rounded-full bg-green-400 mr-4 flex-shrink-0"
                style={{ boxShadow: "0 0 6px #4ade80" }}
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium">{term.issue_name || term.issue_id}</p>
                <p className="text-sm text-muted-foreground">
                  <span className="text-primary">{term.project_name || term.project_id}</span>
                  {" · "}Started {formatAge(term.created_at)}
                </p>
              </div>
              <div className="flex gap-2 ml-4">
                <Button variant="outline" size="sm" asChild>
                  <Link
                    to="/projects/$projectId/issues/$issueId"
                    params={{ projectId: term.project_id, issueId: term.issue_id }}
                  >
                    <ExternalLink className="size-3 mr-1" />
                    Go to Issue
                  </Link>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => handleKill(term.id)}
                >
                  <Skull className="size-3 mr-1" />
                  Kill
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
