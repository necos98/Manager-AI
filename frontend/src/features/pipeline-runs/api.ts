import { apiGet, apiPost, apiDelete } from "@/shared/api/client";
import type { PipelineMessage, PipelineMessageCreate, PipelineRun, PipelineRunStart } from "@/shared/types";

export function startPipelineRun(data: PipelineRunStart): Promise<PipelineRun> {
  return apiPost<PipelineRun>("/pipeline-runs", data);
}

export function fetchPipelineRuns(issueId: string): Promise<PipelineRun[]> {
  return apiGet<PipelineRun[]>(`/pipeline-runs?issue_id=${encodeURIComponent(issueId)}`);
}

export function fetchPipelineRun(runId: string): Promise<PipelineRun> {
  return apiGet<PipelineRun>(`/pipeline-runs/${runId}`);
}

export function cancelPipelineRun(runId: string): Promise<null> {
  return apiDelete(`/pipeline-runs/${runId}`);
}

export function fetchPipelineMessages(runId: string): Promise<PipelineMessage[]> {
  return apiGet<PipelineMessage[]>(`/pipeline-runs/${runId}/messages`);
}

export function fetchActivePipelineRuns(issueIds: string[]): Promise<Record<string, { pipeline_name: string; status: string } | null>> {
  return apiGet(`/pipeline-runs/active-by-issue?issue_ids=${issueIds.join(",")}`);
}

export function sendPipelineMessage(runId: string, data: PipelineMessageCreate): Promise<PipelineMessage> {
  return apiPost<PipelineMessage>(`/pipeline-runs/${runId}/messages`, data);
}
