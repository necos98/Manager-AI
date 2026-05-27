import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";
import type { Agent, AgentCreate, AgentUpdate } from "@/shared/types";

export function fetchAgents(projectId: string): Promise<Agent[]> {
  return apiGet<Agent[]>(`/projects/${projectId}/agents`);
}

export function fetchAgent(projectId: string, agentId: string): Promise<Agent> {
  return apiGet<Agent>(`/projects/${projectId}/agents/${agentId}`);
}

export function createAgent(projectId: string, data: AgentCreate): Promise<Agent> {
  return apiPost<Agent>(`/projects/${projectId}/agents`, data);
}

export function updateAgent(projectId: string, agentId: string, data: AgentUpdate): Promise<Agent> {
  return apiPut<Agent>(`/projects/${projectId}/agents/${agentId}`, data);
}

export function deleteAgent(projectId: string, agentId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/agents/${agentId}`);
}

export function seedAgents(projectId: string): Promise<Agent[]> {
  return apiPost<Agent[]>(`/projects/${projectId}/agents/seed`);
}
