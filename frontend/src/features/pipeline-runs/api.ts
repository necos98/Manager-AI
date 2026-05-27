import { apiGet, apiPost, apiDelete } from "@/shared/api/client";
import type { PipelineMessage, PipelineMessageCreate, PipelineRun, PipelineRunStart } from "@/shared/types";

export function startPipelineRun(projectId: string, data: PipelineRunStart): Promise<PipelineRun> {
  return apiPost<PipelineRun>(`/projects/${projectId}/pipeline-runs`, data);
}

export function fetchPipelineRuns(projectId: string, issueId: string): Promise<PipelineRun[]> {
  return apiGet<PipelineRun[]>(`/projects/${projectId}/pipeline-runs?issue_id=${encodeURIComponent(issueId)}`);
}

export function fetchPipelineRun(projectId: string, runId: string): Promise<PipelineRun> {
  return apiGet<PipelineRun>(`/projects/${projectId}/pipeline-runs/${runId}`);
}

export function cancelPipelineRun(projectId: string, runId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/pipeline-runs/${runId}`);
}

export function fetchPipelineMessages(projectId: string, runId: string): Promise<PipelineMessage[]> {
  return apiGet<PipelineMessage[]>(`/projects/${projectId}/pipeline-runs/${runId}/messages`);
}

export function sendPipelineMessage(projectId: string, runId: string, data: PipelineMessageCreate): Promise<PipelineMessage> {
  return apiPost<PipelineMessage>(`/projects/${projectId}/pipeline-runs/${runId}/messages`, data);
}
