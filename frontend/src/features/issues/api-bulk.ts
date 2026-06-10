import { apiPatch, apiPost } from "@/shared/api/client";

export type TagMode = "add" | "remove" | "set";

export interface BulkStatusUpdate {
  issue_ids: string[];
  status: string;
}

export interface BulkTagsUpdate {
  issue_ids: string[];
  tags: string[];
  mode: TagMode;
}

export interface BulkDeleteRequest {
  issue_ids: string[];
}

export interface BulkPriorityUpdate {
  issue_ids: string[];
  priority: number;
}

export interface BulkCategoryUpdate {
  issue_ids: string[];
  category: string | null;
}

export interface BulkResponse {
  updated: number;
  deleted: number;
  errors: Record<string, string>;
}

export function bulkUpdateStatus(projectId: string, data: BulkStatusUpdate): Promise<BulkResponse> {
  return apiPatch<BulkResponse>(`/projects/${projectId}/issues/bulk/status`, data);
}

export function bulkUpdateTags(projectId: string, data: BulkTagsUpdate): Promise<BulkResponse> {
  return apiPatch<BulkResponse>(`/projects/${projectId}/issues/bulk/tags`, data);
}

export function bulkDeleteIssues(projectId: string, data: BulkDeleteRequest): Promise<BulkResponse> {
  return apiPost<BulkResponse>(`/projects/${projectId}/issues/bulk/delete`, data);
}

export function bulkUpdatePriority(projectId: string, data: BulkPriorityUpdate): Promise<BulkResponse> {
  return apiPatch<BulkResponse>(`/projects/${projectId}/issues/bulk/priority`, data);
}

export function bulkUpdateCategory(projectId: string, data: BulkCategoryUpdate): Promise<BulkResponse> {
  return apiPatch<BulkResponse>(`/projects/${projectId}/issues/bulk/category`, data);
}
