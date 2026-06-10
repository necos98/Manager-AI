import { apiGet, apiPost } from "@/shared/api/client";

export interface QueuedIssueItem {
  position: number;
  issue_id: string;
  issue_name: string;
  issue_description: string;
  project_id: string;
  project_name: string;
  created_at: string;
}

export interface RunningIssueItem {
  issue_id: string;
  issue_name: string | null;
  project_id: string;
  project_name: string | null;
  terminal_id: string;
  issue_status: string | null;
  started_at: string | null;
}

export interface QueueStatus {
  queued_count: number;
  running_count: number;
  dispatching_count: number;
  paused: boolean;
  auto_process_enabled: boolean;
}

export interface QueueResponse {
  queued: QueuedIssueItem[];
  total: number;
}

export interface RunningResponse {
  running: RunningIssueItem[];
  total: number;
}

export function fetchGlobalQueue(): Promise<QueueResponse> {
  return apiGet<QueueResponse>("/queue");
}

export function fetchGlobalRunning(): Promise<RunningResponse> {
  return apiGet<RunningResponse>("/queue/running");
}

export function fetchQueueStatus(): Promise<QueueStatus> {
  return apiGet<QueueStatus>("/queue/status");
}

export function setAutoProcess(enabled: boolean): Promise<{ enabled: boolean }> {
  return apiPost("/queue/auto-process", { enabled });
}

export function addToQueue(projectId: string, issueId: string): Promise<{ id: string; message: string }> {
  return apiPost("/queue/add", { project_id: projectId, issue_id: issueId });
}

export function removeFromQueue(projectId: string, issueId: string): Promise<{ id: string; message: string }> {
  return apiPost("/queue/remove", { project_id: projectId, issue_id: issueId });
}

export interface QueuePositionResponse {
  position: number | null;
  issue_id: string;
  in_queue: boolean;
  status: string;
}

export function fetchQueuePosition(issueId: string, projectId: string): Promise<QueuePositionResponse> {
  return apiGet<QueuePositionResponse>(`/queue/position/${issueId}?project_id=${projectId}`);
}
