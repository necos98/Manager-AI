import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api-plugins";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

const pluginKeys = {
  catalog: () => ["plugins", "catalog"] as const,
  list: (projectId: string) => ["plugins", projectId] as const,
  detail: (projectId: string, key: string) => ["plugins", projectId, key] as const,
};

export function useCatalog() {
  return useQuery({
    queryKey: pluginKeys.catalog(),
    queryFn: api.fetchCatalog,
    staleTime: 5 * 60 * 1000,
  });
}

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
    mutationFn: ({ key, enabled, config }: { key: string; enabled: boolean; config: Record<string, string> }) =>
      api.upsertPlugin(projectId, key, { enabled, config }),
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

export function useTestPluginConnection(projectId: string) {
  return useMutation({
    mutationFn: ({ key, config }: { key: string; config: Record<string, string> }) =>
      api.testPluginConnection(projectId, key, config),
  });
}
