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
import { useCreateTerminal } from "@/features/terminals/hooks";

interface PipelineRunButtonProps {
  projectId: string;
  issueId: string;
  disabled?: boolean;
}

export function PipelineRunButton({ projectId, issueId, disabled }: PipelineRunButtonProps) {
  const { data: pipelines } = usePipelines(projectId);
  const createTerminal = useCreateTerminal();

  const [selectedPipelineId, setSelectedPipelineId] = useState("");

  const hasPipelines = pipelines && pipelines.length > 0;

  const handleRun = () => {
    if (!selectedPipelineId || createTerminal.isPending) return;
    createTerminal.mutate(
      {
        issue_id: issueId,
        project_id: projectId,
        command: `claude --dangerously-skip-permissions "/run-pipeline ${issueId}"`,
      },
      { onSuccess: () => setSelectedPipelineId("") }
    );
  };

  const tooltip = !hasPipelines ? "No pipelines configured" : "";

  return (
    <div className="flex items-center gap-1">
      <Select
        value={selectedPipelineId}
        onValueChange={setSelectedPipelineId}
        disabled={disabled || createTerminal.isPending}
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
        variant="outline"
        onClick={handleRun}
        disabled={disabled || !selectedPipelineId || createTerminal.isPending}
        title={tooltip || undefined}
      >
        {createTerminal.isPending ? (
          <Loader2 className="size-4 mr-1 animate-spin" />
        ) : (
          <Play className="size-4 mr-1" />
        )}
        {createTerminal.isPending ? "Starting..." : "Run Pipeline"}
      </Button>
    </div>
  );
}
