import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api-templates";

export const templateKeys = {
  project: (id: string) => ["projects", id, "templates"] as const,
};

export function useProjectTemplates(projectId: string) {
  return useQuery({
    queryKey: templateKeys.project(projectId),
    queryFn: () => api.fetchProjectTemplates(projectId),
    enabled: !!projectId,
  });
}

export function useSaveTemplate(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ type, content }: { type: string; content: string }) =>
      api.saveTemplateOverride(projectId, type, { content }),
    onSuccess: () => qc.invalidateQueries({ queryKey: templateKeys.project(projectId) }),
  });
}

export function useDeleteTemplate(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (type: string) => api.deleteTemplateOverride(projectId, type),
    onSuccess: () => qc.invalidateQueries({ queryKey: templateKeys.project(projectId) }),
  });
}
