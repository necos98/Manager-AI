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
