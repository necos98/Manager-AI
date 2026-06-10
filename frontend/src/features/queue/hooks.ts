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
