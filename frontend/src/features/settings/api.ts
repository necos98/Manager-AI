import { apiGet, apiPut, apiDelete, apiPost } from "@/shared/api/client";
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

export function installHermesMcp(): Promise<{
  success: boolean;
  message?: string;
  error?: string;
  stdout?: string;
  stderr?: string;
  exit_code: number;
}> {
  return apiPost("/system/install-hermes-mcp");
}
