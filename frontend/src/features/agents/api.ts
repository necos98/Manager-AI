import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";
import type { Agent, AgentCreate, AgentUpdate } from "@/shared/types";

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
