import { useDroppable } from "@dnd-kit/core";
import { KanbanCard } from "./kanban-card";
import { StatusBadge } from "./status-badge";
import type { Issue, IssueStatus } from "@/shared/types";

interface KanbanColumnProps {
  status: IssueStatus;
  issues: Issue[];
  activeTerminalIssueIds: string[];
  blockedIssueIds: Set<string>;
  isValidTarget: boolean;
}

export function KanbanColumn({ status, issues, activeTerminalIssueIds, blockedIssueIds, isValidTarget }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div className="flex flex-col min-w-[220px] flex-1">
      <div className="flex items-center gap-2 mb-3">
        <StatusBadge status={status} />
        <span className="text-xs text-muted-foreground">{issues.length}</span>
      </div>
      <div
        ref={setNodeRef}
        className={[
          "flex-1 rounded-lg p-2 min-h-[120px] space-y-2 transition-colors",
          isOver && isValidTarget ? "bg-primary/10 ring-1 ring-primary" : "bg-muted/30",
          isOver && !isValidTarget ? "bg-destructive/10 ring-1 ring-destructive" : "",
        ].join(" ")}
      >
        {issues.map((issue) => (
          <KanbanCard
            key={issue.id}
            issue={issue}
            hasTerminal={activeTerminalIssueIds.includes(issue.id)}
            isBlocked={blockedIssueIds.has(issue.id)}
          />
        ))}
      </div>
    </div>
  );
}
