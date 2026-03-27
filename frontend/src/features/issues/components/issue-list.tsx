import { Link } from "@tanstack/react-router";
import { StatusBadge } from "./status-badge";
import type { Issue } from "@/shared/types";

interface IssueListProps {
  issues: Issue[];
  projectId: string;
  activeTerminalIssueIds: string[];
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
    <div className="space-y-1">
      {issues.map((issue) => {
        const hasTerminal = activeTerminalIssueIds.includes(issue.id);
        return (
          <Link
            key={issue.id}
            to="/projects/$projectId/issues/$issueId"
            params={{ projectId, issueId: issue.id }}
            className="flex items-center justify-between rounded-md border px-4 py-3 hover:bg-accent transition-colors"
          >
            <div className="flex items-center flex-1 min-w-0">
              {hasTerminal && (
                <span
                  className="w-2 h-2 rounded-full bg-green-400 mr-3 flex-shrink-0"
                  style={{ boxShadow: "0 0 6px #4ade80" }}
                  title="Terminal active"
                />
              )}
              <div className="min-w-0">
                <p className="font-medium truncate">
                  {issue.name || issue.description}
                </p>
                {issue.name && (
                  <p className="text-sm text-muted-foreground truncate">
                    {issue.description}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3 ml-4">
              <span className="text-sm text-muted-foreground">P{issue.priority}</span>
              <StatusBadge status={issue.status} />
            </div>
          </Link>
        );
      })}
    </div>
  );
}
