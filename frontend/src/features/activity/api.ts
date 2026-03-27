import { request } from "@/shared/api/client";
import type { ActivityLog } from "@/shared/types";

export function fetchActivity(
  projectId: string,
  params?: { issue_id?: string; limit?: number; offset?: number }
): Promise<ActivityLog[]> {
  const query = new URLSearchParams();
  if (params?.issue_id) query.set("issue_id", params.issue_id);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  if (params?.offset !== undefined) query.set("offset", String(params.offset));
  const qs = query.toString();
  return request(`/projects/${projectId}/activity${qs ? `?${qs}` : ""}`);
}
