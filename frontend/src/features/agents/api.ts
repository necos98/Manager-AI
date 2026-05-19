import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";

export interface AgentData {
  id: string;
  project_id: string;
  name: string;
  role_key: string;
  system_prompt: string;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface PipelineStepData {
  agent_id: string;
  order: number;
}

export interface PipelineData {
  id: string;
  project_id: string;
  name: string;
  steps: PipelineStepData[];
  is_default: boolean;
  trigger_type: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface PipelineRunData {
  id: string;
  status: string;
  trigger_type: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface PipelineRunFullData {
  run: {
    id: string;
    pipeline_id: string;
    issue_id: string | null;
    trigger_type: string;
    status: string;
    started_at: string | null;
    completed_at: string | null;
  };
  steps: PipelineStepRunData[];
}

export interface PipelineStepRunData {
  id: string;
  agent_name: string;
  agent_role: string;
  step_order: number;
  status: string;
  summary: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

// Agents
export function fetchAgents(projectId: string): Promise<AgentData[]> {
  return apiGet<AgentData[]>(`/projects/${projectId}/agents`);
}

export function createAgent(projectId: string, data: { name: string; role_key: string; system_prompt?: string }): Promise<AgentData> {
  return apiPost<AgentData>(`/projects/${projectId}/agents`, data);
}

export function updateAgent(projectId: string, agentId: string, data: Record<string, unknown>): Promise<AgentData> {
  return apiPut<AgentData>(`/projects/${projectId}/agents/${agentId}`, data);
}

export function deleteAgent(projectId: string, agentId: string): Promise<void> {
  return apiDelete(`/projects/${projectId}/agents/${agentId}`);
}

// Pipelines
export function fetchPipelines(projectId: string): Promise<{ pipelines: PipelineData[] }> {
  return apiGet<{ pipelines: PipelineData[] }>(`/projects/${projectId}/pipelines`);
}

export function createPipeline(projectId: string, data: { name: string; steps: PipelineStepData[]; is_default?: boolean; trigger_type?: string }): Promise<PipelineData> {
  return apiPost<PipelineData>(`/projects/${projectId}/pipelines`, data);
}

export function updatePipeline(projectId: string, pipelineId: string, data: Record<string, unknown>): Promise<PipelineData> {
  return apiPut<PipelineData>(`/projects/${projectId}/pipelines/${pipelineId}`, data);
}

export function deletePipeline(projectId: string, pipelineId: string): Promise<void> {
  return apiDelete(`/projects/${projectId}/pipelines/${pipelineId}`);
}

// Pipeline Runs
export function fetchPipelineRun(runId: string): Promise<PipelineRunFullData> {
  return apiGet<PipelineRunFullData>(`/projects/_/pipelines/runs/${runId}`);
}

export function fetchPipelineRunsForIssue(projectId: string, issueId: string): Promise<{ runs: PipelineRunData[] }> {
  return apiGet<{ runs: PipelineRunData[] }>(`/projects/${projectId}/pipelines/runs/by-issue/${issueId}`);
}
