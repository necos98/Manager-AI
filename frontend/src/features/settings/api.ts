import { apiGet, apiPut, apiDelete, apiPost } from "@/shared/api/client";
import type { HermesCommand, Setting } from "@/shared/types";

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
  commands?: string[];
  message?: string;
}> {
  return apiPost("/system/install-hermes-mcp");
}

export function installHermesSkills(): Promise<{
  success: boolean;
  copied: { name: string; status: string }[];
  path: string;
  message: string;
}> {
  return apiPost("/system/install-hermes-skills");
}

export async function fetchHermesCommands(): Promise<HermesCommand[]> {
  const settings = await fetchSettings();
  const raw = settings.find((s) => s.key === "hermes_commands")?.value;
  if (!raw) return [];
  try {
    return JSON.parse(raw) as HermesCommand[];
  } catch {
    return [];
  }
}
