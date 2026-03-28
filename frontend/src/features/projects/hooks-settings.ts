import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api-settings";

export const projectSettingKeys = {
  all: (projectId: string) => ["project-settings", projectId] as const,
};

export function useProjectSettings(projectId: string) {
  return useQuery({
    queryKey: projectSettingKeys.all(projectId),
    queryFn: () => api.fetchProjectSettings(projectId),
    enabled: !!projectId,
  });
}

export function useSetProjectSetting(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      api.setProjectSetting(projectId, key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectSettingKeys.all(projectId) });
    },
  });
}

export function useDeleteProjectSetting(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => api.deleteProjectSetting(projectId, key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectSettingKeys.all(projectId) });
    },
  });
}
