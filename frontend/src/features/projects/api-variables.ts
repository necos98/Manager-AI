import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";
import type { ProjectVariable, ProjectVariableCreate, ProjectVariableUpdate } from "@/shared/types";

export function fetchProjectVariables(projectId: string): Promise<ProjectVariable[]> {
  return apiGet<ProjectVariable[]>(`/project-variables?project_id=${projectId}`);
}

export function createProjectVariable(
  projectId: string,
  data: ProjectVariableCreate
): Promise<ProjectVariable> {
  return apiPost<ProjectVariable>(`/project-variables?project_id=${projectId}`, data);
}

export function updateProjectVariable(
  varId: number,
  data: ProjectVariableUpdate
): Promise<ProjectVariable> {
  return apiPut<ProjectVariable>(`/project-variables/${varId}`, data);
}

export function deleteProjectVariable(varId: number): Promise<null> {
  return apiDelete(`/project-variables/${varId}`);
}

export function revealProjectVariable(varId: number): Promise<ProjectVariable> {
  return apiGet<ProjectVariable>(`/project-variables/${varId}/reveal`);
}
