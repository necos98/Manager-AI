import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useActivity } from "@/features/activity/hooks";
import { useIssues } from "@/features/issues/hooks";
import { ActivityTimeline } from "@/features/activity/components/activity-timeline";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/$projectId/activity")({
  component: ActivityPage,
});

function ActivityPage() {
  const { projectId } = Route.useParams();
  const [selectedIssueId, setSelectedIssueId] = useState<string | undefined>(undefined);

  const { data: logs, isLoading, error } = useActivity(projectId, selectedIssueId);
  const { data: issues } = useIssues(projectId);

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-32" />
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-destructive">{(error as Error).message}</div>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Activity</h1>
        <select
          value={selectedIssueId ?? ""}
          onChange={(e) => setSelectedIssueId(e.target.value || undefined)}
          className="text-sm border rounded-md px-2 py-1 bg-background"
        >
          <option value="">All issues</option>
          {(issues ?? []).map((issue) => (
            <option key={issue.id} value={issue.id}>
              {issue.name || issue.description.slice(0, 50)}
            </option>
          ))}
        </select>
      </div>
      <ActivityTimeline logs={logs ?? []} />
    </div>
  );
}
