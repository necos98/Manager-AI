import { Check, Loader2, X, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { usePipelineRunsForIssue, usePipelineRun } from "../hooks";

interface PipelineProgressProps {
  projectId: string;
  issueId: string;
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  pending: <span className="size-3 rounded-full bg-gray-400" />,
  running: <Loader2 className="size-4 text-blue-500 animate-spin" />,
  completed: <Check className="size-4 text-green-500" />,
  failed: <X className="size-4 text-red-500" />,
};

const LINE_COLOR: Record<string, string> = {
  pending: "bg-gray-300",
  running: "bg-blue-300",
  completed: "bg-green-300",
  failed: "bg-red-300",
};

export function PipelineProgress({ projectId, issueId }: PipelineProgressProps) {
  const { data, isLoading } = usePipelineRunsForIssue(projectId, issueId);
  const runs = data?.runs ?? [];
  const latestRun = runs[0];

  const { data: runData } = usePipelineRun(latestRun?.id ?? null);
  const steps = runData?.steps ?? [];

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

  const runningIdx = steps.findIndex((s) => s.status === "running");
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const currentStep = runningIdx >= 0 ? steps[runningIdx] : null;

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium">Pipeline Run</h3>
            <div className="flex items-center gap-2 text-xs">
              <span className="capitalize text-muted-foreground">{latestRun.status}</span>
              {currentStep && (
                <>
                  <ChevronRight className="size-3 text-muted-foreground" />
                  <span>
                    Step {runningIdx + 1}/{steps.length} — {currentStep.agent_name}
                  </span>
                </>
              )}
              {latestRun.status === "completed" && (
                <span className="text-green-600 font-medium">
                  {completedCount}/{steps.length} completed
                </span>
              )}
            </div>
          </div>

          {steps.length > 0 ? (
            <div className="space-y-0">
              {steps.map((step, i) => {
                const isLast = i === steps.length - 1;
                return (
                  <div key={step.id} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="flex items-center justify-center size-6 rounded-full border-2 border-muted bg-background shrink-0">
                        {STATUS_ICON[step.status] || STATUS_ICON.pending}
                      </div>
                      {!isLast && (
                        <div className={`w-0.5 flex-1 min-h-[24px] ${LINE_COLOR[step.status] || "bg-gray-300"}`} />
                      )}
                    </div>
                    <div className={`pb-4 flex-1 min-w-0 ${isLast ? "" : ""}`}>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{step.agent_name}</span>
                        <span className="text-xs text-muted-foreground">{step.agent_role}</span>
                      </div>
                      {step.summary && (
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2" title={step.summary}>
                          {step.summary}
                        </p>
                      )}
                      {step.error && (
                        <p className="text-xs text-red-600 mt-0.5 line-clamp-2" title={step.error}>
                          {step.error}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground text-center py-4">
              Step data loading...
            </p>
          )}
        </CardContent>
      </Card>

      {runs.length > 1 && (
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground mb-2">Previous runs</p>
            {runs.slice(1).map((r) => (
              <div key={r.id} className="flex items-center gap-2 text-xs py-1">
                <span className={`size-2 rounded-full ${r.status === "completed" ? "bg-green-500" : r.status === "failed" ? "bg-red-500" : "bg-gray-400"}`} />
                <span className="capitalize">{r.status}</span>
                <span className="text-muted-foreground">
                  {r.started_at ? new Date(r.started_at).toLocaleDateString() : ""}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
