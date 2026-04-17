import { apiGet, apiPost, apiPut } from "@/shared/api/client";
import type { SkillCreate, SkillDetail, SkillMeta } from "@/shared/types";

export function fetchSkills(): Promise<SkillMeta[]> {
  return apiGet<SkillMeta[]>("/library/skills");
}

export function fetchAgents(): Promise<SkillMeta[]> {
  return apiGet<SkillMeta[]>("/library/agents");
}

export function fetchSkill(name: string, type: string): Promise<SkillDetail> {
  const endpoint = type === "agent" ? `/library/agents/${name}` : `/library/skills/${name}`;
  return apiGet<SkillDetail>(endpoint);
}

export function createSkill(data: SkillCreate): Promise<SkillMeta> {
  const endpoint = data.type === "agent" ? "/library/agents" : "/library/skills";
  return apiPost<SkillMeta>(endpoint, data);
}

export function updateSkill(name: string, type: string, content: string): Promise<null> {
  const endpoint = type === "agent" ? `/library/agents/${name}` : `/library/skills/${name}`;
  return apiPut<null>(endpoint, { content });
}
