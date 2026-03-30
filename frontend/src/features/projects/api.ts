import { request } from "@/shared/api/client";
import type { Project, ProjectCreate, ProjectUpdate } from "@/shared/types";

export function fetchProjects(): Promise<Project[]> {
  return request("/projects");
}

export function fetchProject(projectId: string): Promise<Project> {
  return request(`/projects/${projectId}`);
}

export function createProject(data: ProjectCreate): Promise<Project> {
  return request("/projects", { method: "POST", body: JSON.stringify(data) });
}

export function updateProject(projectId: string, data: ProjectUpdate): Promise<Project> {
  return request(`/projects/${projectId}`, { method: "PUT", body: JSON.stringify(data) });
}

export function deleteProject(projectId: string): Promise<null> {
  return request(`/projects/${projectId}`, { method: "DELETE" });
}

export function installManagerJson(projectId: string): Promise<{ path: string }> {
  return request(`/projects/${projectId}/install-manager-json`, { method: "POST" });
}

export function installClaudeResources(projectId: string): Promise<{ path: string; copied: string[] }> {
  return request(`/projects/${projectId}/install-claude-resources`, { method: "POST" });
}
