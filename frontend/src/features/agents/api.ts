import { apiGet, apiPost, apiPut, apiDelete, buildUrl, uploadRequest } from "@/shared/api/client";
import type { Agent, AgentCreate, AgentUpdate, ImportConfirmResponse, ImportPreviewResponse, AgentExportItem } from "@/shared/types";

export function fetchAgents(): Promise<Agent[]> {
  return apiGet<Agent[]>("/agents");
}

export function fetchAgent(agentId: string): Promise<Agent> {
  return apiGet<Agent>(`/agents/${agentId}`);
}

export function createAgent(data: AgentCreate): Promise<Agent> {
  return apiPost<Agent>("/agents", data);
}

export function updateAgent(agentId: string, data: AgentUpdate): Promise<Agent> {
  return apiPut<Agent>(`/agents/${agentId}`, data);
}

export function deleteAgent(agentId: string): Promise<null> {
  return apiDelete(`/agents/${agentId}`);
}

export function seedAgents(): Promise<Agent[]> {
  return apiPost<Agent[]>("/agents/seed");
}

export async function exportAgents(): Promise<Blob> {
  const res = await fetch(buildUrl("/agents/export"));
  return res.blob();
}

export async function exportAgent(agentId: string): Promise<Blob> {
  const res = await fetch(buildUrl(`/agents/export/${agentId}`));
  return res.blob();
}

export function importAgentsPreview(file: File): Promise<ImportPreviewResponse<AgentExportItem>> {
  const fd = new FormData();
  fd.append("file", file);
  return uploadRequest<ImportPreviewResponse<AgentExportItem>>("/agents/import/preview", fd);
}

export function importAgentsConfirm(
  file: File,
  conflicts: Record<string, string>,
): Promise<ImportConfirmResponse> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("conflicts", JSON.stringify(conflicts));
  return uploadRequest<ImportConfirmResponse>("/agents/import/confirm", fd);
}
