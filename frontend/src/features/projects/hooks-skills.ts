import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api-skills";
import type { ProjectSkillAssign } from "@/shared/types";

export const skillKeys = {
  project: (id: string) => ["projects", id, "skills"] as const,
};

export function useProjectSkills(projectId: string) {
  return useQuery({
    queryKey: skillKeys.project(projectId),
    queryFn: () => api.fetchProjectSkills(projectId),
    enabled: !!projectId,
  });
}

export function useAssignSkill(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectSkillAssign) => api.assignSkill(projectId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: skillKeys.project(projectId) }),
  });
}

export function useUnassignSkill(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ type, name }: { type: string; name: string }) =>
      api.unassignSkill(projectId, type, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: skillKeys.project(projectId) }),
  });
}
