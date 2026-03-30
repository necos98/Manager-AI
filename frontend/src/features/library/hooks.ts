import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { SkillCreate } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const libraryKeys = {
  skills: ["library", "skills"] as const,
  agents: ["library", "agents"] as const,
  skill: (name: string, type: string) => ["library", "skill", name, type] as const,
  agent: (name: string) => ["library", "agent", name] as const,
};

export function useSkills() {
  return useQuery({ queryKey: libraryKeys.skills, queryFn: api.fetchSkills });
}

export function useAgents() {
  return useQuery({ queryKey: libraryKeys.agents, queryFn: api.fetchAgents });
}

export function useSkillDetail(name: string, type: string) {
  return useQuery({
    queryKey: libraryKeys.skill(name, type),
    queryFn: () => api.fetchSkill(name, type),
    enabled: !!name,
  });
}

export function useAgentDetail(name: string) {
  return useQuery({
    queryKey: libraryKeys.agent(name),
    queryFn: () => api.fetchSkill(name, "agent"),
    enabled: !!name,
  });
}

export function useCreateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillCreate) => api.createSkill(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: libraryKeys.skills });
      qc.invalidateQueries({ queryKey: libraryKeys.agents });
    },
    onError: onMutationError,
  });
}

export function useUpdateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, type, content }: { name: string; type: string; content: string }) =>
      api.updateSkill(name, type, content),
    onSuccess: (_data, { name, type }) => {
      qc.invalidateQueries({ queryKey: libraryKeys.skills });
      qc.invalidateQueries({ queryKey: libraryKeys.agents });
      qc.invalidateQueries({ queryKey: libraryKeys.skill(name, type) });
    },
    onError: onMutationError,
  });
}
