import { apiGet } from "@/shared/api/client";
import type { SystemInfo } from "@/shared/types";

export function fetchSystemInfo(): Promise<SystemInfo> {
  return apiGet<SystemInfo>("/system/info");
}
