import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { PipelineMessageCreate, PipelineRunStart } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const pipelineRunKeys = {
  all: (projectId: string) => ["pipeline-runs", projectId] as const,
  byIssue: (projectId: string, issueId: string) => ["pipeline-runs", projectId, "issue", issueId] as const,
  detail: (projectId: string, runId: string) => ["pipeline-runs", projectId, runId] as const,
  messages: (projectId: string, runId: string) => ["pipeline-runs", projectId, runId, "messages"] as const,
};

export function usePipelineRuns(
  projectId: string,
  issueId: string,
  opts?: { refetchInterval?: number | false }
) {
  return useQuery({
    queryKey: pipelineRunKeys.byIssue(projectId, issueId),
    queryFn: () => api.fetchPipelineRuns(projectId, issueId),
    enabled: Boolean(projectId) && Boolean(issueId),
    refetchInterval: opts?.refetchInterval,
  });
}

export function usePipelineRun(projectId: string, runId: string) {
  return useQuery({
    queryKey: pipelineRunKeys.detail(projectId, runId),
    queryFn: () => api.fetchPipelineRun(projectId, runId),
    enabled: Boolean(projectId) && Boolean(runId),
  });
}

export function useStartPipelineRun(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PipelineRunStart) => api.startPipelineRun(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineRunKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useCancelPipelineRun(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.cancelPipelineRun(projectId, runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineRunKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function usePipelineMessages(
  projectId: string,
  runId: string,
  opts?: { refetchInterval?: number | false }
) {
  return useQuery({
    queryKey: pipelineRunKeys.messages(projectId, runId),
    queryFn: () => api.fetchPipelineMessages(projectId, runId),
    enabled: Boolean(projectId) && Boolean(runId),
    refetchInterval: opts?.refetchInterval,
  });
}

export function useSendPipelineMessage(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, data }: { runId: string; data: PipelineMessageCreate }) =>
      api.sendPipelineMessage(projectId, runId, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: pipelineRunKeys.messages(projectId, variables.runId) });
    },
    onError: onMutationError,
  });
}
