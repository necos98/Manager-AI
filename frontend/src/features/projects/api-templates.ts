import { request } from "@/shared/api/client";
import type { TemplateInfo, TemplateSave } from "@/shared/types";

export function fetchProjectTemplates(projectId: string): Promise<TemplateInfo[]> {
  return request(`/projects/${projectId}/templates`);
}

export function fetchProjectTemplate(projectId: string, type: string): Promise<TemplateInfo> {
  return request(`/projects/${projectId}/templates/${type}`);
}

export function saveTemplateOverride(
  projectId: string,
  type: string,
  data: TemplateSave,
): Promise<TemplateInfo> {
  return request(`/projects/${projectId}/templates/${type}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteTemplateOverride(projectId: string, type: string): Promise<null> {
  return request(`/projects/${projectId}/templates/${type}`, { method: "DELETE" });
}
