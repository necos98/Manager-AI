import { apiGet, apiPut, apiPost, apiDelete } from "@/shared/api/client";

export interface EnvResponse {
  variables: Record<string, string>;
}

export interface PresetOut {
  id: string;
  name: string;
  variables: Record<string, string>;
  has_secrets: boolean;
  created_at: string;
  updated_at: string;
}

export interface PresetCreate {
  name: string;
  variables: Record<string, string>;
}

export interface PresetUpdate {
  name?: string;
  variables?: Record<string, string>;
}

export function fetchEnv(): Promise<EnvResponse> {
  return apiGet<EnvResponse>("/credentials-editor");
}

export function updateEnv(variables: Record<string, string>): Promise<EnvResponse> {
  return apiPut<EnvResponse>("/credentials-editor", { variables });
}

export function fetchPresets(): Promise<PresetOut[]> {
  return apiGet<PresetOut[]>("/credentials-editor/presets");
}

export function createPreset(data: PresetCreate): Promise<PresetOut> {
  return apiPost<PresetOut>("/credentials-editor/presets", data);
}

export function updatePreset(id: string, data: PresetUpdate): Promise<PresetOut> {
  return apiPut<PresetOut>(`/credentials-editor/presets/${encodeURIComponent(id)}`, data);
}

export function deletePreset(id: string): Promise<null> {
  return apiDelete(`/credentials-editor/presets/${encodeURIComponent(id)}`);
}

export function applyPreset(id: string): Promise<EnvResponse> {
  return apiPost<EnvResponse>(`/credentials-editor/presets/${encodeURIComponent(id)}/apply`);
}
