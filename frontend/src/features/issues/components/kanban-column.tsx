import { useDroppable } from "@dnd-kit/core";
import { KanbanCard } from "./kanban-card";
import { StatusBadge } from "./status-badge";
import { Button } from "@/shared/components/ui/button";
import type { Issue, IssueStatus } from "@/shared/types";

interface KanbanColumnProps {
  status: IssueStatus;
  issues: Issue[];
  activeTerminalIssueIds: string[];
  blockedIssueIds: Set<string>;
  isValidTarget: boolean;
  projectId: string;
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  activeRunsByIssue?: Record<string, { pipeline_name: string; status: string } | null>;
}

export function KanbanColumn({ status, issues, activeTerminalIssueIds, blockedIssueIds, isValidTarget, projectId, onLoadMore, hasMore, isLoadingMore, activeRunsByIssue }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div className="flex flex-col min-w-[220px] flex-1">
      <div className="flex items-center gap-2 mb-3">
        <StatusBadge status={status} />
        <span className="text-xs text-muted-foreground">{issues.length}</span>
      </div>
      <div
        ref={setNodeRef}
        role="region"
        aria-label={`${status} column, ${issues.length} issue${issues.length === 1 ? "" : "s"}`}
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
            projectId={projectId}
            activePipelineName={activeRunsByIssue?.[issue.id]?.pipeline_name}
          />
        ))}
        {onLoadMore && hasMore && (
          <Button variant="ghost" size="sm" onClick={onLoadMore} disabled={isLoadingMore} className="mt-2 w-full">
            {isLoadingMore ? "Loading..." : "Load more"}
          </Button>
        )}
      </div>
    </div>
  );
}
