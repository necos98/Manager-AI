import { request } from "@/shared/api/client";
import type { Setting } from "@/shared/types";

export function fetchSettings(): Promise<Setting[]> {
  return request("/settings");
}

export function updateSetting(key: string, value: string): Promise<Setting> {
  return request(`/settings/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify({ value }) });
}

export function resetSetting(key: string): Promise<null> {
  return request(`/settings/${encodeURIComponent(key)}`, { method: "DELETE" });
}

export function resetAllSettings(): Promise<null> {
  return request("/settings", { method: "DELETE" });
}
