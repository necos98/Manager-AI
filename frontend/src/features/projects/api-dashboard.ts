import { request } from "@/shared/api/client";
import type { DashboardProject } from "@/shared/types";

export function fetchDashboard(): Promise<DashboardProject[]> {
  return request("/dashboard");
}
