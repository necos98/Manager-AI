import { Link } from "@tanstack/react-router";
import { Terminal } from "lucide-react";
import { Card } from "@/shared/components/ui/card";
import { StatusBadge } from "./status-badge";
import type { Issue } from "@/shared/types";

interface IssueListProps {
  issues: Issue[];
  projectId: string;
  activeTerminalIssueIds: string[];
}

function TaskProgress({ tasks }: { tasks: Issue["tasks"] }) {
  if (!tasks || tasks.length === 0) return null;

  const completed = tasks.filter((t) => t.status === "Completed").length;
  const total = tasks.length;
  const percent = Math.round((completed / total) * 100);

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap">
        {completed}/{total}
      </span>
    </div>
  );
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function IssueList({ issues, projectId, activeTerminalIssueIds }: IssueListProps) {
  if (issues.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No issues yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {issues.map((issue) => {
        const hasTerminal = activeTerminalIssueIds.includes(issue.id);
        return (
          <Link
            key={issue.id}
            to="/projects/$projectId/issues/$issueId"
            params={{ projectId, issueId: issue.id }}
            className="block"
          >
            <Card className="px-4 py-3 hover:bg-accent/50 transition-colors cursor-pointer">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    {hasTerminal && (
                      <Terminal
                        className="size-3.5 text-green-500 flex-shrink-0"
                        style={{ filter: "drop-shadow(0 0 4px #4ade80)" }}
                      />
                    )}
                    <p className="font-medium truncate">
                      {issue.name || issue.description}
                    </p>
                  </div>
                  {issue.name && (
                    <p className="text-sm text-muted-foreground truncate mt-0.5">
                      {issue.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs text-muted-foreground">P{issue.priority}</span>
                  <StatusBadge status={issue.status} />
                </div>
              </div>

              <div className="flex items-center justify-between mt-2.5 gap-4">
                <div className="flex-1 max-w-48">
                  <TaskProgress tasks={issue.tasks} />
                </div>
                <span className="text-xs text-muted-foreground">
                  {timeAgo(issue.updated_at)}
                </span>
              </div>
            </Card>
          </Link>
        );
      })}
    </div>
  );
}
