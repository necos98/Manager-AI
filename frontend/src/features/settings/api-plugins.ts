import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";

// ── Catalog types ────────────────────────────────────────────────────────────

export interface PluginOption {
  key: string;
  label: string;
  type: "string" | "secret" | "number" | "boolean" | "select";
  required: boolean;
  default: string;
  placeholder: string;
  choices?: { value: string; label: string }[];
}

export interface CatalogPlugin {
  key: string;
  name: string;
  description: string;
  transport: string;
  access_level: string;
  options: PluginOption[];
}

// ── Project plugin types ─────────────────────────────────────────────────────

export interface PluginInfo {
  key: string;
  name: string;
  description: string;
  enabled: boolean;
  transport: string;
  access_level: string;
  connected: boolean;
  tool_count: number;
  configured: boolean;
  config: Record<string, string>;
  catalog: boolean;
  legacy?: boolean;
}

export interface PluginDetail {
  key: string;
  name: string;
  description: string;
  enabled: boolean;
  transport: string;
  access_level: string;
  config: Record<string, string>;
  catalog: boolean;
}

// ── API functions ────────────────────────────────────────────────────────────

export function fetchCatalog(): Promise<CatalogPlugin[]> {
  return apiGet<CatalogPlugin[]>("/plugins/catalog");
}

export function fetchPlugins(projectId: string): Promise<PluginInfo[]> {
  return apiGet<PluginInfo[]>(`/projects/${projectId}/plugins`);
}

export function fetchPlugin(projectId: string, key: string): Promise<PluginDetail> {
  return apiGet<PluginDetail>(`/projects/${projectId}/plugins/${encodeURIComponent(key)}`);
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

export interface TestConnectionResult {
  success: boolean;
  message: string;
  tools?: string[];
}

export function testPluginConnection(projectId: string, key: string, config: Record<string, string>): Promise<TestConnectionResult> {
  return apiPost<TestConnectionResult>(`/projects/${projectId}/plugins/${encodeURIComponent(key)}/test`, { config });
}
