import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";
import type { Project, ProjectCreate, ProjectUpdate, Terminal } from "@/shared/types";

export interface ProjectHealth {
  manager_json: { installed: boolean; path: string };
  claude_resources: { installed: boolean; path: string; missing: string[] };
  mcp: { installed: boolean; location: string | null };
}

export function fetchProjectHealth(projectId: string): Promise<ProjectHealth> {
  return apiGet<ProjectHealth>(`/projects/${projectId}/health`);
}

export function installMcp(projectId: string): Promise<Terminal> {
  return apiPost<Terminal>(`/projects/${projectId}/install-mcp`);
}

export function fetchProjects(archived: boolean = false): Promise<Project[]> {
  const query = archived ? "?archived=true" : "";
  return apiGet<Project[]>(`/projects${query}`);
}

export function archiveProject(projectId: string): Promise<Project> {
  return apiPost<Project>(`/projects/${projectId}/archive`);
}

export function unarchiveProject(projectId: string): Promise<Project> {
  return apiPost<Project>(`/projects/${projectId}/unarchive`);
}

export function fetchProject(projectId: string): Promise<Project> {
  return apiGet<Project>(`/projects/${projectId}`);
}

export function createProject(data: ProjectCreate): Promise<Project> {
  return apiPost<Project>("/projects", data);
}

export function updateProject(projectId: string, data: ProjectUpdate): Promise<Project> {
  return apiPut<Project>(`/projects/${projectId}`, data);
}

export function deleteProject(projectId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}`);
}

export function installManagerJson(projectId: string): Promise<{ path: string }> {
  return apiPost<{ path: string }>(`/projects/${projectId}/install-manager-json`);
}

export function installClaudeResources(projectId: string): Promise<{ path: string; copied: string[] }> {
  return apiPost<{ path: string; copied: string[] }>(`/projects/${projectId}/install-claude-resources`);
}

export interface CodebaseIndexStatus {
  indexed: boolean;
  file_count: number;
}

export function fetchCodebaseIndexStatus(projectId: string): Promise<CodebaseIndexStatus> {
  return apiGet<CodebaseIndexStatus>(`/projects/${projectId}/codebase-index-status`);
}

export function triggerCodebaseIndex(projectId: string): Promise<{ status: string }> {
  return apiPost<{ status: string }>(`/projects/${projectId}/index-codebase`);
}
