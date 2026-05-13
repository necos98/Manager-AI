import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api-plugins";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

const pluginKeys = {
  list: (projectId: string) => ["plugins", projectId] as const,
  detail: (projectId: string, key: string) => ["plugins", projectId, key] as const,
};

export function usePlugins(projectId: string) {
  return useQuery({
    queryKey: pluginKeys.list(projectId),
    queryFn: () => api.fetchPlugins(projectId),
    enabled: !!projectId,
  });
}

export function useUpsertPlugin(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, data }: { key: string; data: Record<string, unknown> }) =>
      api.upsertPlugin(projectId, key, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: pluginKeys.list(projectId) }),
    onError: onMutationError,
  });
}

export function useDeletePlugin(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => api.deletePlugin(projectId, key),
    onSuccess: () => qc.invalidateQueries({ queryKey: pluginKeys.list(projectId) }),
    onError: onMutationError,
  });
}

export function useTogglePlugin(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, enabled }: { key: string; enabled: boolean }) =>
      enabled ? api.enablePlugin(projectId, key) : api.disablePlugin(projectId, key),
    onSuccess: () => qc.invalidateQueries({ queryKey: pluginKeys.list(projectId) }),
    onError: onMutationError,
  });
}
