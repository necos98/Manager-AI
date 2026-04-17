import { apiGet, apiPost, apiDelete } from "@/shared/api/client";
import type { ProjectSkill, ProjectSkillAssign } from "@/shared/types";

export function fetchProjectSkills(projectId: string): Promise<ProjectSkill[]> {
  return apiGet<ProjectSkill[]>(`/projects/${projectId}/skills`);
}

export function assignSkill(projectId: string, data: ProjectSkillAssign): Promise<ProjectSkill> {
  return apiPost<ProjectSkill>(`/projects/${projectId}/skills`, data);
}

export function unassignSkill(projectId: string, type: string, name: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/skills/${type}/${name}`);
}
