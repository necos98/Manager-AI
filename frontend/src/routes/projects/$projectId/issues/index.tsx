import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useIssues } from "@/features/issues/hooks";
import { useProject } from "@/features/projects/hooks";
import { useTerminals } from "@/features/terminals/hooks";
import { IssueList } from "@/features/issues/components/issue-list";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import type { IssueStatus } from "@/shared/types";

const STATUSES: Array<IssueStatus | "All"> = [
  "All",
  "New",
  "Reasoning",
  "Planned",
  "Accepted",
  "Finished",
  "Canceled",
];

export const Route = createFileRoute("/projects/$projectId/issues/")({
  component: IssuesPage,
});

function IssuesPage() {
  const { projectId } = Route.useParams();
  const [filter, setFilter] = useState<IssueStatus | "All">("All");

  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Issues - ${project.name}` : "Issues";
  }, [project]);

  const { data: issues, isLoading } = useIssues(
    projectId,
    filter === "All" ? undefined : filter,
  );
  const { data: terminals } = useTerminals(projectId);

  const activeTerminalIssueIds = terminals?.map((t) => t.issue_id) ?? [];

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          {project && (
            <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
          )}
          <h1 className="text-xl font-semibold">Issues</h1>
        </div>
        <Button asChild size="sm">
          <Link
            to="/projects/$projectId/issues/new"
            params={{ projectId }}
          >
            <Plus className="size-4 mr-1" />
            New Issue
          </Link>
        </Button>
      </div>

      <div className="flex gap-1.5 mb-4 flex-wrap">
        {STATUSES.map((s) => (
          <Button
            key={s}
            variant={filter === s ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(s)}
            className="text-xs"
          >
            {s}
          </Button>
        ))}
      </div>

      <IssueList
        issues={issues ?? []}
        projectId={projectId}
        activeTerminalIssueIds={activeTerminalIssueIds}
      />
    </div>
  );
}
