import { request } from "@/shared/api/client";
import type { Issue, IssueCreate, IssueStatus, IssueStatusUpdate, IssueUpdate, Task, TaskCreate, TaskUpdate } from "@/shared/types";

export function fetchIssues(projectId: string, status?: IssueStatus): Promise<Issue[]> {
  const params = status ? `?status=${status}` : "";
  return request(`/projects/${projectId}/issues${params}`);
}

export function fetchIssue(projectId: string, issueId: string): Promise<Issue> {
  return request(`/projects/${projectId}/issues/${issueId}`);
}

export function createIssue(projectId: string, data: IssueCreate): Promise<Issue> {
  return request(`/projects/${projectId}/issues`, { method: "POST", body: JSON.stringify(data) });
}

export function updateIssue(projectId: string, issueId: string, data: IssueUpdate): Promise<Issue> {
  return request(`/projects/${projectId}/issues/${issueId}`, { method: "PUT", body: JSON.stringify(data) });
}

export function updateIssueStatus(projectId: string, issueId: string, data: IssueStatusUpdate): Promise<Issue> {
  return request(`/projects/${projectId}/issues/${issueId}/status`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteIssue(projectId: string, issueId: string): Promise<null> {
  return request(`/projects/${projectId}/issues/${issueId}`, { method: "DELETE" });
}

export function fetchTasks(projectId: string, issueId: string): Promise<Task[]> {
  return request(`/projects/${projectId}/issues/${issueId}/tasks`);
}

export function createTasks(projectId: string, issueId: string, tasks: TaskCreate[]): Promise<Task[]> {
  return request(`/projects/${projectId}/issues/${issueId}/tasks`, { method: "POST", body: JSON.stringify({ tasks }) });
}

export function replaceTasks(projectId: string, issueId: string, tasks: TaskCreate[]): Promise<Task[]> {
  return request(`/projects/${projectId}/issues/${issueId}/tasks`, { method: "PUT", body: JSON.stringify({ tasks }) });
}

export function updateTask(projectId: string, issueId: string, taskId: string, data: TaskUpdate): Promise<Task> {
  return request(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteTask(projectId: string, issueId: string, taskId: string): Promise<null> {
  return request(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`, { method: "DELETE" });
}
