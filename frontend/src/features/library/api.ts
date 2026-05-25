import { apiGet, apiPost, apiPut } from "@/shared/api/client";
import type { SkillCreate, SkillDetail, SkillMeta } from "@/shared/types";

export function fetchSkills(): Promise<SkillMeta[]> {
  return apiGet<SkillMeta[]>("/library/skills");
}

export function fetchSkill(name: string): Promise<SkillDetail> {
  return apiGet<SkillDetail>(`/library/skills/${name}`);
}

export function createSkill(data: SkillCreate): Promise<SkillMeta> {
  return apiPost<SkillMeta>("/library/skills", data);
}

export function updateSkill(name: string, content: string): Promise<null> {
  return apiPut<null>(`/library/skills/${name}`, { content });
}
