import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { SkillCreate } from "@/shared/types";

export const libraryKeys = {
  skills: ["library", "skills"] as const,
  agents: ["library", "agents"] as const,
  skill: (name: string) => ["library", "skills", name] as const,
  agent: (name: string) => ["library", "agents", name] as const,
};

export function useSkills() {
  return useQuery({ queryKey: libraryKeys.skills, queryFn: api.fetchSkills });
}

export function useAgents() {
  return useQuery({ queryKey: libraryKeys.agents, queryFn: api.fetchAgents });
}

export function useSkillDetail(name: string) {
  return useQuery({
    queryKey: libraryKeys.skill(name),
    queryFn: () => api.fetchSkill(name),
    enabled: !!name,
  });
}

export function useAgentDetail(name: string) {
  return useQuery({
    queryKey: libraryKeys.agent(name),
    queryFn: () => api.fetchAgent(name),
    enabled: !!name,
  });
}

export function useCreateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillCreate) => api.createSkill(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: libraryKeys.skills }),
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillCreate) => api.createAgent(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: libraryKeys.agents }),
  });
}
