import { request } from "@/shared/api/client";
import type { SkillCreate, SkillDetail, SkillMeta } from "@/shared/types";

export function fetchSkills(): Promise<SkillMeta[]> {
  return request("/library/skills");
}

export function fetchAgents(): Promise<SkillMeta[]> {
  return request("/library/agents");
}

export function fetchSkill(name: string, type: string): Promise<SkillDetail> {
  const endpoint = type === "agent" ? `/library/agents/${name}` : `/library/skills/${name}`;
  return request(endpoint);
}

export function createSkill(data: SkillCreate): Promise<SkillMeta> {
  const endpoint = data.type === "agent" ? "/library/agents" : "/library/skills";
  return request(endpoint, { method: "POST", body: JSON.stringify(data) });
}

export function updateSkill(name: string, type: string, content: string): Promise<null> {
  const endpoint = type === "agent" ? `/library/agents/${name}` : `/library/skills/${name}`;
  return request(endpoint, { method: "PUT", body: JSON.stringify({ content }) });
}
