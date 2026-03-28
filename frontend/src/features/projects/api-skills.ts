import { request } from "@/shared/api/client";
import type { ProjectSkill, ProjectSkillAssign } from "@/shared/types";

export function fetchProjectSkills(projectId: string): Promise<ProjectSkill[]> {
  return request(`/projects/${projectId}/skills`);
}

export function assignSkill(projectId: string, data: ProjectSkillAssign): Promise<ProjectSkill> {
  return request(`/projects/${projectId}/skills`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function unassignSkill(projectId: string, type: string, name: string): Promise<null> {
  return request(`/projects/${projectId}/skills/${type}/${name}`, { method: "DELETE" });
}
