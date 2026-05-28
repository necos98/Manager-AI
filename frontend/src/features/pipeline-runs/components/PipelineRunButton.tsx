import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { usePipelines } from "@/features/pipelines/hooks";
import { usePipelineRuns, useStartPipelineRun } from "@/features/pipeline-runs/hooks";

interface PipelineRunButtonProps {
  projectId: string;
  issueId: string;
  disabled?: boolean;
}

export function PipelineRunButton({ projectId, issueId, disabled }: PipelineRunButtonProps) {
  const { data: pipelines } = usePipelines();
  const { data: runs } = usePipelineRuns(projectId, issueId);
  const startRun = useStartPipelineRun(projectId);

  const [selectedPipelineId, setSelectedPipelineId] = useState("");

  const activeRun = runs?.find((r) => r.status === "RUNNING");
  const hasPipelines = pipelines && pipelines.length > 0;

  const isRunning = startRun.isPending || !!activeRun;

  const handleRun = () => {
    if (!selectedPipelineId || isRunning) return;
    startRun.mutate(
      { pipeline_id: selectedPipelineId, issue_id: issueId, project_id: projectId },
      { onSuccess: () => setSelectedPipelineId("") }
    );
  };

  let tooltip = "";
  if (activeRun) tooltip = "Pipeline already running";
  else if (!hasPipelines) tooltip = "No pipelines configured";

  return (
    <div className="flex items-center gap-1">
      <Select
        value={selectedPipelineId}
        onValueChange={setSelectedPipelineId}
        disabled={disabled || isRunning}
      >
        <SelectTrigger className="h-8 w-44 text-xs" title={tooltip || undefined}>
          <SelectValue placeholder="Select pipeline..." />
        </SelectTrigger>
        <SelectContent>
          {pipelines?.map((p) => (
            <SelectItem key={p.id} value={p.id}>
              {p.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button
        size="sm"
        className="h-8"
        onClick={handleRun}
        disabled={disabled || !selectedPipelineId || isRunning}
        title={tooltip || undefined}
      >
        {startRun.isPending ? (
          <Loader2 className="size-3 mr-1 animate-spin" />
        ) : (
          <Play className="size-3 mr-1" />
        )}
        {activeRun ? "Running" : startRun.isPending ? "Starting..." : "Run Pipeline"}
      </Button>
    </div>
  );
}
