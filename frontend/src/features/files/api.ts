import { buildUrl, request, uploadRequest } from "@/shared/api/client";
import type { AllowedFormats, ProjectFile } from "@/shared/types";

export function fetchAllowedFormats(): Promise<AllowedFormats> {
  return request("/files/allowed-formats");
}

export function fetchFiles(projectId: string): Promise<ProjectFile[]> {
  return request(`/projects/${projectId}/files`);
}

export function uploadFiles(projectId: string, formData: FormData): Promise<ProjectFile[]> {
  return uploadRequest(`/projects/${projectId}/files`, formData);
}

export function getFileDownloadUrl(projectId: string, fileId: string): string {
  return buildUrl(`/projects/${projectId}/files/${fileId}/download`);
}

export function deleteFile(projectId: string, fileId: string): Promise<null> {
  return request(`/projects/${projectId}/files/${fileId}`, { method: "DELETE" });
}
