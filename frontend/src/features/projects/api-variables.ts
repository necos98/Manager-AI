import { request } from "@/shared/api/client";
import type { ProjectVariable, ProjectVariableCreate, ProjectVariableUpdate } from "@/shared/types";

export function fetchProjectVariables(projectId: string): Promise<ProjectVariable[]> {
  return request(`/project-variables?project_id=${projectId}`);
}

export function createProjectVariable(
  projectId: string,
  data: ProjectVariableCreate
): Promise<ProjectVariable> {
  return request(`/project-variables?project_id=${projectId}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateProjectVariable(
  varId: number,
  data: ProjectVariableUpdate
): Promise<ProjectVariable> {
  return request(`/project-variables/${varId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteProjectVariable(varId: number): Promise<null> {
  return request(`/project-variables/${varId}`, { method: "DELETE" });
}
