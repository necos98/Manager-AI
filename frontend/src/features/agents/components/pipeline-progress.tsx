import { Card, CardContent } from "@/shared/components/ui/card";
import { usePipelineRunsForIssue } from "../hooks";

interface PipelineProgressProps {
  projectId: string;
  issueId: string;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "#9ca3af",
  running: "#3b82f6",
  completed: "#22c55e",
  failed: "#ef4444",
};

export function PipelineProgress({ projectId, issueId }: PipelineProgressProps) {
  const { data, isLoading } = usePipelineRunsForIssue(projectId, issueId);
  const runs = data?.runs ?? [];
  const latestRun = runs[0];

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-xs text-muted-foreground">Loading pipeline status...</p>
        </CardContent>
      </Card>
    );
  }

  if (!latestRun) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center py-8">
            No pipeline runs yet for this issue.
          </p>
        </CardContent>
      </Card>
    );
  }

  // For the pipeline progress stepper, we need full step data
  // For now show a summary with the run status
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">
              Pipeline Run
            </h3>
            <div className="flex items-center gap-2">
              <span
                className="size-2.5 rounded-full"
                style={{ backgroundColor: STATUS_COLORS[latestRun.status] || "#6b7280" }}
              />
              <span className="text-xs font-medium capitalize">{latestRun.status}</span>
              <span className="text-xs text-muted-foreground">{latestRun.trigger_type}</span>
            </div>
          </div>

          {runs.length > 1 && (
            <div className="border-t pt-3">
              <p className="text-xs text-muted-foreground mb-2">Previous runs</p>
              {runs.slice(1).map((r) => (
                <div key={r.id} className="flex items-center gap-2 text-xs py-1">
                  <span
                    className="size-2 rounded-full"
                    style={{ backgroundColor: STATUS_COLORS[r.status] || "#6b7280" }}
                  />
                  <span className="capitalize">{r.status}</span>
                  <span className="text-muted-foreground">
                    {r.started_at ? new Date(r.started_at).toLocaleDateString() : ""}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
