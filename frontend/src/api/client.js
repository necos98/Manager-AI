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

  // Tasks
  listTasks: (projectId, status) => {
    const params = status ? `?status=${status}` : "";
    return request(`/projects/${projectId}/tasks${params}`);
  },
  getTask: (projectId, taskId) => request(`/projects/${projectId}/tasks/${taskId}`),
  createTask: (projectId, data) =>
    request(`/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(data) }),
  updateTask: (projectId, taskId, data) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "PUT", body: JSON.stringify(data) }),
  updateTaskStatus: (projectId, taskId, data) =>
    request(`/projects/${projectId}/tasks/${taskId}/status`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTask: (projectId, taskId) =>
    request(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" }),

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
};
