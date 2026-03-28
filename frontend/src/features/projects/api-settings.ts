import { request } from "@/shared/api/client";

export type ProjectSettings = Record<string, string>;

export function fetchProjectSettings(projectId: string): Promise<ProjectSettings> {
  return request(`/projects/${projectId}/settings`);
}

export function setProjectSetting(projectId: string, key: string, value: string): Promise<{ key: string; value: string }> {
  return request(`/projects/${projectId}/settings/${key}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}

export function deleteProjectSetting(projectId: string, key: string): Promise<null> {
  return request(`/projects/${projectId}/settings/${key}`, {
    method: "DELETE",
  });
}
