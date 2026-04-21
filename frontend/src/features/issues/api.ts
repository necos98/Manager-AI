import { apiGet, apiPost, apiPut, apiPatch, apiDelete } from "@/shared/api/client";
import type {
  Issue,
  IssueCreate,
  IssueCompleteBody,
  IssueFeedback,
  IssueFeedbackCreate,
  IssueStatus,
  IssueStatusUpdate,
  IssueUpdate,
  Task,
  TaskCreate,
  TaskUpdate,
} from "@/shared/types";

export function fetchIssues(
  projectId: string,
  status?: IssueStatus,
  search?: string
): Promise<Issue[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (search) params.set("search", search);
  const qs = params.toString();
  return apiGet<Issue[]>(`/projects/${projectId}/issues${qs ? `?${qs}` : ""}`);
}

export function fetchIssue(projectId: string, issueId: string): Promise<Issue> {
  return apiGet<Issue>(`/projects/${projectId}/issues/${issueId}`);
}

export function createIssue(projectId: string, data: IssueCreate): Promise<Issue> {
  return apiPost<Issue>(`/projects/${projectId}/issues`, data);
}

export function updateIssue(projectId: string, issueId: string, data: IssueUpdate): Promise<Issue> {
  return apiPut<Issue>(`/projects/${projectId}/issues/${issueId}`, data);
}

export function updateIssueStatus(projectId: string, issueId: string, data: IssueStatusUpdate): Promise<Issue> {
  return apiPatch<Issue>(`/projects/${projectId}/issues/${issueId}/status`, data);
}

export function deleteIssue(projectId: string, issueId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/issues/${issueId}`);
}

export function fetchTasks(projectId: string, issueId: string): Promise<Task[]> {
  return apiGet<Task[]>(`/projects/${projectId}/issues/${issueId}/tasks`);
}

export function createTasks(projectId: string, issueId: string, tasks: TaskCreate[]): Promise<Task[]> {
  return apiPost<Task[]>(`/projects/${projectId}/issues/${issueId}/tasks`, { tasks });
}

export function replaceTasks(projectId: string, issueId: string, tasks: TaskCreate[]): Promise<Task[]> {
  return apiPut<Task[]>(`/projects/${projectId}/issues/${issueId}/tasks`, { tasks });
}

export function updateTask(projectId: string, issueId: string, taskId: string, data: TaskUpdate): Promise<Task> {
  return apiPatch<Task>(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`, data);
}

export function deleteTask(projectId: string, issueId: string, taskId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`);
}


export function acceptIssue(projectId: string, issueId: string): Promise<Issue> {
  return apiPost<Issue>(`/projects/${projectId}/issues/${issueId}/accept`);
}

export function cancelIssue(projectId: string, issueId: string): Promise<Issue> {
  return apiPost<Issue>(`/projects/${projectId}/issues/${issueId}/cancel`);
}

export function completeIssue(projectId: string, issueId: string, data: IssueCompleteBody): Promise<Issue> {
  return apiPost<Issue>(`/projects/${projectId}/issues/${issueId}/complete`, data);
}

export function fetchFeedback(projectId: string, issueId: string): Promise<IssueFeedback[]> {
  return apiGet<IssueFeedback[]>(`/projects/${projectId}/issues/${issueId}/feedback`);
}

export function addFeedback(projectId: string, issueId: string, data: IssueFeedbackCreate): Promise<IssueFeedback> {
  return apiPost<IssueFeedback>(`/projects/${projectId}/issues/${issueId}/feedback`, data);
}
