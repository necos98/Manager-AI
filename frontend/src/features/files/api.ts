import { apiGet, apiPost, apiDelete, buildUrl, uploadRequest } from "@/shared/api/client";
import type { AllowedFormats, ProjectFile } from "@/shared/types";

export function fetchAllowedFormats(): Promise<AllowedFormats> {
  return apiGet<AllowedFormats>("/files/allowed-formats");
}

export function fetchFiles(projectId: string): Promise<ProjectFile[]> {
  return apiGet<ProjectFile[]>(`/projects/${projectId}/files`);
}

export function uploadFiles(projectId: string, formData: FormData): Promise<ProjectFile[]> {
  return uploadRequest(`/projects/${projectId}/files`, formData);
}

export function getFileDownloadUrl(projectId: string, fileId: string): string {
  return buildUrl(`/projects/${projectId}/files/${fileId}/download`);
}

export function deleteFile(projectId: string, fileId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/files/${fileId}`);
}

export function reindexFile(projectId: string, fileId: string): Promise<ProjectFile> {
  return apiPost<ProjectFile>(`/projects/${projectId}/files/${fileId}/reindex`);
}
