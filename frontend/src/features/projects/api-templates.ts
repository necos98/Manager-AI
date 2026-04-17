import { apiGet, apiPut, apiDelete } from "@/shared/api/client";
import type { TemplateInfo, TemplateSave } from "@/shared/types";

export function fetchProjectTemplates(projectId: string): Promise<TemplateInfo[]> {
  return apiGet<TemplateInfo[]>(`/projects/${projectId}/templates`);
}

export function fetchProjectTemplate(projectId: string, type: string): Promise<TemplateInfo> {
  return apiGet<TemplateInfo>(`/projects/${projectId}/templates/${type}`);
}

export function saveTemplateOverride(
  projectId: string,
  type: string,
  data: TemplateSave,
): Promise<TemplateInfo> {
  return apiPut<TemplateInfo>(`/projects/${projectId}/templates/${type}`, data);
}

export function deleteTemplateOverride(projectId: string, type: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/templates/${type}`);
}
