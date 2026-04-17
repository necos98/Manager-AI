import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useIssues } from "@/features/issues/hooks";
import { NewIssueDialog } from "@/features/issues/components/new-issue-dialog";
import { useBlockedIssueIds } from "@/features/issues/hooks-relations";
import { useProject } from "@/features/projects/hooks";
import { useTerminals } from "@/features/terminals/hooks";
import { KanbanBoard } from "@/features/issues/components/kanban-board";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { ErrorBoundary } from "@/shared/components/error-boundary";

export const Route = createFileRoute("/projects/$projectId/issues/")({
  component: IssuesPage,
});

function IssuesPage() {
  const { projectId } = Route.useParams();
  const [newIssueOpen, setNewIssueOpen] = useState(false);
  const { data: project } = useProject(projectId);

  useEffect(() => {
    document.title = project ? `Issues - ${project.name}` : "Issues";
  }, [project]);

  const { data: issues, isLoading } = useIssues(projectId);
  const { data: terminals } = useTerminals(projectId);
  const activeTerminalIssueIds = terminals?.map((t) => t.issue_id) ?? [];
  const blockedIssueIds = useBlockedIssueIds(issues ?? []);

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16" />)}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          {project && <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>}
          <h1 className="text-xl font-semibold">Issues</h1>
        </div>
        <Button size="sm" onClick={() => setNewIssueOpen(true)}>
          <Plus className="size-4 mr-1" />
          New Issue
        </Button>
      </div>
      <ErrorBoundary>
        <KanbanBoard
          issues={issues ?? []}
          projectId={projectId}
          activeTerminalIssueIds={activeTerminalIssueIds}
          blockedIssueIds={blockedIssueIds}
        />
      </ErrorBoundary>
      <NewIssueDialog
        projectId={projectId}
        open={newIssueOpen}
        onOpenChange={setNewIssueOpen}
      />
    </div>
  );
}
