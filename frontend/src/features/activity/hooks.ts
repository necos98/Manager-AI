import { useQuery } from "@tanstack/react-query";
import * as api from "./api";

export const activityKeys = {
  list: (projectId: string, issueId?: string) =>
    ["projects", projectId, "activity", { issueId }] as const,
};

export function useActivity(projectId: string, issueId?: string) {
  return useQuery({
    queryKey: activityKeys.list(projectId, issueId),
    queryFn: () => api.fetchActivity(projectId, issueId ? { issue_id: issueId } : undefined),
  });
}
