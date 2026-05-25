import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { SkillCreate } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const libraryKeys = {
  skills: ["library", "skills"] as const,
  skill: (name: string) => ["library", "skill", name] as const,
};

export function useSkills() {
  return useQuery({ queryKey: libraryKeys.skills, queryFn: api.fetchSkills });
}

export function useSkillDetail(name: string) {
  return useQuery({
    queryKey: libraryKeys.skill(name),
    queryFn: () => api.fetchSkill(name),
    enabled: !!name,
  });
}

export function useCreateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillCreate) => api.createSkill(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: libraryKeys.skills });
    },
    onError: onMutationError,
  });
}

export function useUpdateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) =>
      api.updateSkill(name, content),
    onSuccess: (_data, { name }) => {
      qc.invalidateQueries({ queryKey: libraryKeys.skills });
      qc.invalidateQueries({ queryKey: libraryKeys.skill(name) });
    },
    onError: onMutationError,
  });
}
