import { Link } from "@tanstack/react-router";
import { Skull } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { TerminalPanel } from "./terminal-panel";
import type { TerminalListItem } from "@/shared/types";

interface TerminalGridProps {
  terminals: TerminalListItem[];
  onKill: (id: string) => void;
}

function getGridClass(count: number): string {
  if (count === 1) return "grid-cols-1";
  if (count === 2) return "grid-cols-2";
  return "grid-cols-[repeat(auto-fill,minmax(500px,1fr))]";
}

export function TerminalGrid({ terminals, onKill }: TerminalGridProps) {
  if (terminals.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Nessun terminale attivo.</p>
      </div>
    );
  }

  const gridClass = getGridClass(terminals.length);

  return (
    <div className={`grid ${gridClass} gap-3 h-full`}>
      {terminals.map((term) => (
        <div key={term.id} className="flex flex-col border rounded-lg overflow-hidden min-h-[400px]">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-1.5 border-b bg-muted/30 flex-shrink-0">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0"
                style={{ boxShadow: "0 0 4px #4ade80" }}
              />
              <span className="text-sm font-medium truncate">{term.issue_name || term.issue_id}</span>
              <span className="text-xs text-muted-foreground flex-shrink-0">{term.project_name}</span>
            </div>
            <div className="flex gap-1 flex-shrink-0 ml-2">
              <Button variant="ghost" size="sm" asChild className="h-6 text-xs px-2">
                <Link
                  to="/projects/$projectId/issues/$issueId"
                  params={{ projectId: term.project_id, issueId: term.issue_id }}
                >
                  Issue
                </Link>
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground hover:text-destructive"
                onClick={() => onKill(term.id)}
              >
                <Skull className="size-3" />
              </Button>
            </div>
          </div>
          {/* Terminal */}
          <div className="flex-1 min-h-0">
            <TerminalPanel terminalId={term.id} />
          </div>
        </div>
      ))}
    </div>
  );
}
