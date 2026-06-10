import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

export const queueKeys = {
  all: ["queue"] as const,
  queued: ["queue", "queued"] as const,
  running: ["queue", "running"] as const,
  status: ["queue", "status"] as const,
};

export function useGlobalQueue() {
  return useQuery({
    queryKey: queueKeys.queued,
    queryFn: api.fetchGlobalQueue,
    refetchInterval: 5_000,
  });
}

export function useGlobalRunning() {
  return useQuery({
    queryKey: queueKeys.running,
    queryFn: api.fetchGlobalRunning,
    refetchInterval: 5_000,
  });
}

export function useQueueStatus() {
  return useQuery({
    queryKey: queueKeys.status,
    queryFn: api.fetchQueueStatus,
    refetchInterval: 10_000,
  });
}

export function useSetAutoProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) => api.setAutoProcess(enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queueKeys.status });
    },
  });
}

export function useQueuePosition(issueId: string, projectId: string) {
  return useQuery({
    queryKey: [...queueKeys.all, "position", issueId],
    queryFn: () => api.fetchQueuePosition(issueId, projectId),
    enabled: Boolean(issueId) && Boolean(projectId),
    refetchInterval: 10_000,
  });
}

export function useAddToQueue() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, issueId }: { projectId: string; issueId: string }) =>
      api.addToQueue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queueKeys.queued });
      queryClient.invalidateQueries({ queryKey: queueKeys.status });
      queryClient.invalidateQueries({ queryKey: queueKeys.all });
    },
  });
}

export function useRemoveFromQueue() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, issueId }: { projectId: string; issueId: string }) =>
      api.removeFromQueue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queueKeys.queued });
      queryClient.invalidateQueries({ queryKey: queueKeys.status });
      queryClient.invalidateQueries({ queryKey: queueKeys.all });
    },
  });
}
