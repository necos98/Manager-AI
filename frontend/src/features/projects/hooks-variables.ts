import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api-variables";
import type { ProjectVariableCreate, ProjectVariableUpdate } from "@/shared/types";

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
  });
}

export function useUpdateProjectVariable(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProjectVariableUpdate }) =>
      api.updateProjectVariable(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: varKeys.list(projectId) }),
  });
}

export function useDeleteProjectVariable(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (varId: number) => api.deleteProjectVariable(varId),
    onSuccess: () => qc.invalidateQueries({ queryKey: varKeys.list(projectId) }),
  });
}
