const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (res.status === 204) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  // Projects
  listProjects: () => request("/projects"),
  getProject: (id) => request(`/projects/${id}`),
  createProject: (data) => request("/projects", { method: "POST", body: JSON.stringify(data) }),
  updateProject: (id, data) => request(`/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProject: (id) => request(`/projects/${id}`, { method: "DELETE" }),
  installManagerJson: (id) => request(`/projects/${id}/install-manager-json`, { method: "POST" }),
  installClaudeResources: (id) => request(`/projects/${id}/install-claude-resources`, { method: "POST" }),

  // Issues (ex Tasks)
  listIssues: (projectId, status) => {
    const params = status ? `?status=${status}` : "";
    return request(`/projects/${projectId}/issues${params}`);
  },
  getIssue: (projectId, issueId) => request(`/projects/${projectId}/issues/${issueId}`),
  createIssue: (projectId, data) =>
    request(`/projects/${projectId}/issues`, { method: "POST", body: JSON.stringify(data) }),
  updateIssue: (projectId, issueId, data) =>
    request(`/projects/${projectId}/issues/${issueId}`, { method: "PUT", body: JSON.stringify(data) }),
  updateIssueStatus: (projectId, issueId, data) =>
    request(`/projects/${projectId}/issues/${issueId}/status`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteIssue: (projectId, issueId) =>
    request(`/projects/${projectId}/issues/${issueId}`, { method: "DELETE" }),

  // Tasks (atomic plan tasks)
  listTasks: (projectId, issueId) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks`),
  createTasks: (projectId, issueId, tasks) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks`, { method: "POST", body: JSON.stringify({ tasks }) }),
  replaceTasks: (projectId, issueId, tasks) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks`, { method: "PUT", body: JSON.stringify({ tasks }) }),
  updateTask: (projectId, issueId, taskId, data) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTask: (projectId, issueId, taskId) =>
    request(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`, { method: "DELETE" }),

  // Settings
  getSettings: () => request("/settings"),
  updateSetting: (key, value) =>
    request(`/settings/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
  resetSetting: (key) =>
    request(`/settings/${encodeURIComponent(key)}`, { method: "DELETE" }),
  resetAllSettings: () => request("/settings", { method: "DELETE" }),

  // Terminals
  listTerminals: (projectId, issueId) => {
    const params = new URLSearchParams();
    if (projectId) params.set("project_id", projectId);
    if (issueId) params.set("issue_id", issueId);
    const qs = params.toString();
    return request(`/terminals${qs ? `?${qs}` : ""}`);
  },
  createTerminal: (issueId, projectId) =>
    request("/terminals", { method: "POST", body: JSON.stringify({ issue_id: issueId, project_id: projectId }) }),
  killTerminal: (terminalId) =>
    request(`/terminals/${terminalId}`, { method: "DELETE" }),
  terminalCount: () => request("/terminals/count"),
  terminalConfig: () => request("/terminals/config"),

  // Terminal Commands
  terminalCommandVariables: () => request("/terminal-commands/variables"),
  listTerminalCommands: (projectId) => {
    const params = projectId != null ? `?project_id=${projectId}` : "";
    return request(`/terminal-commands${params}`);
  },
  createTerminalCommand: (data) =>
    request("/terminal-commands", { method: "POST", body: JSON.stringify(data) }),
  updateTerminalCommand: (id, data) =>
    request(`/terminal-commands/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  reorderTerminalCommands: (commands) =>
    request("/terminal-commands/reorder", { method: "PUT", body: JSON.stringify({ commands }) }),
  deleteTerminalCommand: (id) =>
    request(`/terminal-commands/${id}`, { method: "DELETE" }),
};
