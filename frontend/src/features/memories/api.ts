import { apiGet } from "@/shared/api/client";
import type { Memory, MemoryDetail, MemorySearchHit } from "@/shared/types";

export function fetchMemories(projectId: string, parentId?: string | null): Promise<Memory[]> {
  const qs = new URLSearchParams();
  if (parentId !== undefined && parentId !== null) qs.set("parent_id", parentId);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiGet<Memory[]>(`/projects/${projectId}/memories${suffix}`);
}

export function fetchMemory(memoryId: string): Promise<MemoryDetail> {
  return apiGet<MemoryDetail>(`/memories/${memoryId}`);
}

export function searchMemories(projectId: string, query: string, limit = 20): Promise<MemorySearchHit[]> {
  const qs = new URLSearchParams({ q: query, limit: String(limit) });
  return apiGet<MemorySearchHit[]>(`/projects/${projectId}/memories/search?${qs.toString()}`);
}
