import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";
import type { CredentialUpsert, Project, ProjectCreate, ProjectCredential, ProjectLink, ProjectLinkCreate, ProjectLinkUpdate, ProjectUpdate, Terminal } from "@/shared/types";

export interface ProjectHealth {
  manager_json: { installed: boolean; path: string };
  claude_resources: { installed: boolean; path: string; missing: string[] };
  mcp: { installed: boolean; location: string | null };
  playwright_mcp: { installed: boolean; location: string | null };
}

export function fetchProjectHealth(projectId: string): Promise<ProjectHealth> {
  return apiGet<ProjectHealth>(`/projects/${projectId}/health`);
}

export function installMcp(projectId: string): Promise<Terminal> {
  return apiPost<Terminal>(`/projects/${projectId}/install-mcp`);
}

export function installPlaywrightMcp(projectId: string): Promise<Terminal> {
  return apiPost<Terminal>(`/projects/${projectId}/install-playwright-mcp`);
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

export interface RebuildIndexResponse {
  issues: number;
  memories: number;
  files: number;
}

export function rebuildIndex(projectId: string): Promise<RebuildIndexResponse> {
  return apiPost<RebuildIndexResponse>(`/projects/${projectId}/rebuild-index`);
}

export function fetchCodebaseIndexStatus(projectId: string): Promise<CodebaseIndexStatus> {
  return apiGet<CodebaseIndexStatus>(`/projects/${projectId}/codebase-index-status`);
}

export function triggerCodebaseIndex(projectId: string): Promise<{ status: string }> {
  return apiPost<{ status: string }>(`/projects/${projectId}/index-codebase`);
}

export function fetchCredentials(projectId: string): Promise<string[]> {
  return apiGet<string[]>(`/projects/${projectId}/credentials`);
}

export function fetchCredential(projectId: string, role: string): Promise<ProjectCredential> {
  return apiGet<ProjectCredential>(`/projects/${projectId}/credentials/${encodeURIComponent(role)}`);
}

export function upsertCredential(projectId: string, data: CredentialUpsert): Promise<ProjectCredential> {
  return apiPost<ProjectCredential>(`/projects/${projectId}/credentials`, data);
}

export function deleteCredential(projectId: string, role: string): Promise<void> {
  return apiDelete(`/projects/${projectId}/credentials/${encodeURIComponent(role)}`);
}

export function fetchProjectLinks(projectId: string): Promise<ProjectLink[]> {
  return apiGet<ProjectLink[]>(`/projects/${projectId}/links`);
}

export function createProjectLink(projectId: string, data: ProjectLinkCreate): Promise<ProjectLink> {
  return apiPost<ProjectLink>(`/projects/${projectId}/links`, data);
}

export function updateProjectLink(projectId: string, linkId: string, data: ProjectLinkUpdate): Promise<ProjectLink> {
  return apiPut<ProjectLink>(`/projects/${projectId}/links/${linkId}`, data);
}

export function deleteProjectLink(projectId: string, linkId: string): Promise<void> {
  return apiDelete(`/projects/${projectId}/links/${linkId}`);
}
