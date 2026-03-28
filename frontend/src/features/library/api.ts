import { request } from "@/shared/api/client";
import type { SkillCreate, SkillDetail, SkillMeta } from "@/shared/types";

export function fetchSkills(): Promise<SkillMeta[]> {
  return request("/library/skills");
}

export function fetchAgents(): Promise<SkillMeta[]> {
  return request("/library/agents");
}

export function fetchSkill(name: string, type: string): Promise<SkillDetail> {
  return request(`/library/skills/${name}?type=${type}`);
}

export function fetchAgent(name: string): Promise<SkillDetail> {
  return request(`/library/agents/${name}`);
}

export function createSkill(data: SkillCreate): Promise<SkillDetail> {
  return request("/library/skills", { method: "POST", body: JSON.stringify(data) });
}

export function createAgent(data: SkillCreate): Promise<SkillMeta> {
  return request("/library/agents", { method: "POST", body: JSON.stringify(data) });
}

export function updateSkill(name: string, type: string, content: string): Promise<SkillDetail> {
  return request(`/library/skills/${name}`, { method: "PUT", body: JSON.stringify({ type, content }) });
}
