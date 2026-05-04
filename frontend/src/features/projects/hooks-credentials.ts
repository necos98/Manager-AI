import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { CredentialUpsert } from "@/shared/types";
import { projectKeys } from "./hooks";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const credentialKeys = {
  list: (projectId: string) => ["projects", projectId, "credentials"] as const,
  detail: (projectId: string, role: string) =>
    ["projects", projectId, "credentials", role] as const,
};

export function useCredentials(projectId: string) {
  return useQuery({
    queryKey: credentialKeys.list(projectId),
    queryFn: () => api.fetchCredentials(projectId),
    enabled: !!projectId,
  });
}

export function useCredential(projectId: string, role: string) {
  return useQuery({
    queryKey: credentialKeys.detail(projectId, role),
    queryFn: () => api.fetchCredential(projectId, role),
    enabled: !!projectId && !!role,
  });
}

export function useUpsertCredential(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CredentialUpsert) => api.upsertCredential(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: credentialKeys.list(projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
    },
    onError: onMutationError,
  });
}

export function useDeleteCredential(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (role: string) => api.deleteCredential(projectId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: credentialKeys.list(projectId) });
    },
    onError: onMutationError,
  });
}
