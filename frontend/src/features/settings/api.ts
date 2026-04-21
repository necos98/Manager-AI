import { apiGet, apiPut, apiDelete } from "@/shared/api/client";
import type { Setting } from "@/shared/types";

export function fetchSettings(): Promise<Setting[]> {
  return apiGet<Setting[]>("/settings");
}

export function updateSetting(key: string, value: string): Promise<Setting> {
  return apiPut<Setting>(`/settings/${encodeURIComponent(key)}`, { value });
}

export function resetSetting(key: string): Promise<null> {
  return apiDelete(`/settings/${encodeURIComponent(key)}`);
}

export function resetAllSettings(): Promise<null> {
  return apiDelete("/settings");
}
