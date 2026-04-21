import { apiGet, apiPut, apiDelete } from "@/shared/api/client";

export type ProjectSettings = Record<string, string>;

export function fetchProjectSettings(projectId: string): Promise<ProjectSettings> {
  return apiGet<ProjectSettings>(`/projects/${projectId}/settings`);
}

export function setProjectSetting(projectId: string, key: string, value: string): Promise<{ key: string; value: string }> {
  return apiPut<{ key: string; value: string }>(`/projects/${projectId}/settings/${key}`, { value });
}

export function deleteProjectSetting(projectId: string, key: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/settings/${key}`);
}
