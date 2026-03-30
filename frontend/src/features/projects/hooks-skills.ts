import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api-skills";
import type { ProjectSkillAssign } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const skillKeys = {
  project: (id: string) => ["project-skills", id] as const,
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
    onError: onMutationError,
  });
}

export function useUnassignSkill(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ type, name }: { type: string; name: string }) =>
      api.unassignSkill(projectId, type, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: skillKeys.project(projectId) }),
    onError: onMutationError,
  });
}
