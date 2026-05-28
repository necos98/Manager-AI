import { useState, useEffect, useCallback } from "react";
import { XCircle, CheckCircle, Circle, Loader2, Clock, X } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { usePipelineRuns, useCancelPipelineRun } from "@/features/pipeline-runs/hooks";
import { useEvents } from "@/shared/context/event-context";
import type { PipelineRun, PipelineStepRun } from "@/shared/types";

interface PipelineProgressProps {
  projectId: string;
  issueId: string;
  onClose?: () => void;
}

function StepStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "COMPLETED":
      return <CheckCircle className="size-4 text-green-500" />;
    case "RUNNING":
      return <Loader2 className="size-4 text-blue-500 animate-spin" />;
    case "FAILED":
      return <XCircle className="size-4 text-red-500" />;
    default:
      return <Circle className="size-4 text-muted-foreground" />;
  }
}

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "RUNNING"
      ? "default"
      : status === "COMPLETED"
        ? "secondary"
        : status === "FAILED"
          ? "destructive"
          : "outline";
  return (
    <Badge variant={variant as "default" | "secondary" | "destructive" | "outline"} className="text-xs">
      {status}
    </Badge>
  );
}

function formatDuration(startedAt: string | null, finishedAt: string | null): string {
  if (!startedAt) return "";
  const start = new Date(startedAt).getTime();
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  const ms = end - start;
  if (ms < 1000) return "0s";
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  return `${mins}m ${secs % 60}s`;
}

export function PipelineProgress({ projectId, issueId, onClose }: PipelineProgressProps) {
  const { data: runs, isLoading } = usePipelineRuns(projectId, issueId, { refetchInterval: 2000 });
  const cancelRun = useCancelPipelineRun(projectId);
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  const activeRun = runs?.find((r) => r.status === "RUNNING") ?? null;
  const [terminalIds, setTerminalIds] = useState<Record<string, string>>({});

  const { subscribe } = useEvents() ?? {};

  // Auto-select running step when pipeline data updates
  useEffect(() => {
    if (activeRun?.steps) {
      const runningStep = activeRun.steps.find((s) => s.status === "RUNNING");
      if (runningStep) {
        setSelectedStepId(runningStep.id);
      }
    }
  }, [activeRun?.id, activeRun?.steps?.find((s) => s.status === "RUNNING")?.id]);

  // Listen for agent_step_started events to react immediately
  useEffect(() => {
    if (!subscribe) return;
    const unsub = subscribe((event) => {
      if (
        event.type === "agent_step_started" &&
        event.project_id === projectId &&
        event.issue_id === issueId &&
        typeof event.step_run_id === "string"
      ) {
        setSelectedStepId(event.step_run_id);
        if (typeof event.terminal_id === "string") {
          setTerminalIds((prev) => ({ ...prev, [event.step_run_id!]: event.terminal_id! }));
        }
      }
    });
    return unsub;
  }, [subscribe, projectId, issueId]);

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!activeRun) {
    // Show last completed/failed run summary if any
    const lastRun = runs?.[0];
    if (!lastRun) return null;

    const isCompleted = lastRun.status === "COMPLETED";
    return (
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">
              Pipeline {isCompleted ? "Complete" : "Failed"}
            </span>
            <Badge variant={isCompleted ? "secondary" : "destructive"} className="text-xs">
              {isCompleted ? "Passed" : "Failed"}
            </Badge>
          </div>
          {onClose && (
            <Button variant="ghost" size="icon" className="size-6" onClick={onClose}>
              <X className="size-3" />
            </Button>
          )}
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="size-3" />
          {formatDuration(lastRun.started_at, lastRun.finished_at)}
        </div>
      </div>
    );
  }

  const steps = [...(activeRun.steps ?? [])].sort((a, b) => {
    const aIdx = a.started_at ? 1 : 0;
    const bIdx = b.started_at ? 1 : 0;
    return aIdx - bIdx || (a.started_at ?? "").localeCompare(b.started_at ?? "");
  });

  const selectedStep = steps.find((s) => s.id === selectedStepId);
  const selectedTerminalId = selectedStep?.terminal_id || terminalIds[selectedStep?.id || ""];
  const runningStep = steps.find((s) => s.status === "RUNNING");

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">Pipeline</span>
          <Badge variant="default" className="text-xs">
            Running
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs text-destructive hover:text-destructive"
            onClick={() => cancelRun.mutate(activeRun.id)}
            disabled={cancelRun.isPending}
          >
            {cancelRun.isPending ? "Canceling..." : "Cancel"}
          </Button>
          {onClose && (
            <Button variant="ghost" size="icon" className="size-6" onClick={onClose}>
              <X className="size-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Step list */}
      <div className="border-b shrink-0">
        <ScrollArea className="max-h-48">
          {steps.map((step) => (
            <button
              key={step.id}
              onClick={() => setSelectedStepId(step.id)}
              className={`w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-muted/50 transition-colors ${
                step.id === selectedStepId ? "bg-muted" : ""
              } ${step.status === "RUNNING" ? "font-medium" : ""}`}
            >
              <StepStatusIcon status={step.status} />
              <span className="text-sm flex-1">{step.agent_name}</span>
              <StatusBadge status={step.status} />
            </button>
          ))}
        </ScrollArea>
      </div>

      {/* Terminal output */}
      <div className="flex-1 min-h-0">
        {selectedStep && selectedTerminalId ? (
          <TerminalPanel
            terminalId={String(selectedTerminalId)}
            projectId={projectId}
          />
        ) : selectedStep && selectedStep.status === "PENDING" ? (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            Waiting to start...
          </div>
        ) : selectedStep && selectedStep.status === "COMPLETED" ? (
          <div className="flex flex-col items-center justify-center h-full text-sm text-muted-foreground gap-1">
            <CheckCircle className="size-6 text-green-500" />
            <span>Step completed</span>
            <span className="text-xs">
              Duration: {formatDuration(selectedStep.started_at, selectedStep.finished_at)}
            </span>
          </div>
        ) : selectedStep && selectedStep.status === "FAILED" ? (
          <div className="flex flex-col items-center justify-center h-full text-sm text-destructive gap-1">
            <XCircle className="size-6" />
            <span>Step failed</span>
          </div>
        ) : selectedStep ? (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            Output not available
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            Select a step to view output
          </div>
        )}
      </div>
    </div>
  );
}
