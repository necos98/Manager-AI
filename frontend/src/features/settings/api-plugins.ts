import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";

export interface PluginInfo {
  key: string;
  name: string;
  enabled: boolean;
  transport: string;
  access_level: string;
  connected: boolean;
  tool_count: number;
}

export interface PluginConfig {
  key: string;
  name: string;
  enabled: boolean;
  transport: string;
  command: string;
  args: string[];
  url: string;
  env_keys: string[];
  access_level: string;
  timeout: number;
}

export function fetchPlugins(projectId: string): Promise<PluginInfo[]> {
  return apiGet<PluginInfo[]>(`/projects/${projectId}/plugins`);
}

export function fetchPlugin(projectId: string, key: string): Promise<PluginConfig> {
  return apiGet<PluginConfig>(`/projects/${projectId}/plugins/${encodeURIComponent(key)}`);
}

export function upsertPlugin(projectId: string, key: string, data: Record<string, unknown>): Promise<PluginInfo> {
  return apiPut<PluginInfo>(`/projects/${projectId}/plugins/${encodeURIComponent(key)}`, data);
}

export function deletePlugin(projectId: string, key: string): Promise<{ deleted: boolean }> {
  return apiDelete(`/projects/${projectId}/plugins/${encodeURIComponent(key)}`);
}

export function enablePlugin(projectId: string, key: string): Promise<{ success: boolean }> {
  return apiPost<{ success: boolean }>(`/projects/${projectId}/plugins/${encodeURIComponent(key)}/enable`);
}

export function disablePlugin(projectId: string, key: string): Promise<{ success: boolean }> {
  return apiPost<{ success: boolean }>(`/projects/${projectId}/plugins/${encodeURIComponent(key)}/disable`);
}
