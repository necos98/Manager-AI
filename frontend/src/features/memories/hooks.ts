import { useQuery } from "@tanstack/react-query";
import * as api from "@/features/memories/api";

export const memoryKeys = {
  all: (projectId: string) => ["projects", projectId, "memories"] as const,
  list: (projectId: string, parentId?: string | null) =>
    [...memoryKeys.all(projectId), "list", { parentId: parentId ?? null }] as const,
  detail: (memoryId: string) => ["memories", memoryId, "detail"] as const,
  search: (projectId: string, query: string) =>
    [...memoryKeys.all(projectId), "search", query] as const,
};

export function useMemories(projectId: string, parentId?: string | null) {
  return useQuery({
    queryKey: memoryKeys.list(projectId, parentId),
    queryFn: () => api.fetchMemories(projectId, parentId),
    enabled: Boolean(projectId),
  });
}

export function useMemory(memoryId: string | null | undefined) {
  return useQuery({
    queryKey: memoryId ? memoryKeys.detail(memoryId) : ["memories", "none"],
    queryFn: () => api.fetchMemory(memoryId!),
    enabled: Boolean(memoryId),
  });
}

export function useMemorySearch(projectId: string, query: string) {
  return useQuery({
    queryKey: memoryKeys.search(projectId, query),
    queryFn: () => api.searchMemories(projectId, query),
    enabled: Boolean(projectId) && query.trim().length > 0,
    staleTime: 30_000,
  });
}
