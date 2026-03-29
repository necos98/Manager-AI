import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api-variables";
import type { ProjectVariableCreate, ProjectVariableUpdate } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

const varKeys = {
  list: (projectId: string) => ["project-variables", projectId] as const,
};

export function useProjectVariables(projectId: string) {
  return useQuery({
    queryKey: varKeys.list(projectId),
    queryFn: () => api.fetchProjectVariables(projectId),
    enabled: !!projectId,
  });
}

export function useCreateProjectVariable(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectVariableCreate) => api.createProjectVariable(projectId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: varKeys.list(projectId) }),
    onError: onMutationError,
  });
}

export function useUpdateProjectVariable(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProjectVariableUpdate }) =>
      api.updateProjectVariable(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: varKeys.list(projectId) }),
    onError: onMutationError,
  });
}

export function useDeleteProjectVariable(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (varId: number) => api.deleteProjectVariable(varId),
    onSuccess: () => qc.invalidateQueries({ queryKey: varKeys.list(projectId) }),
    onError: onMutationError,
  });
}
