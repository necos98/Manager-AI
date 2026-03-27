# Frontend Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the entire frontend from JavaScript/React Router to TypeScript/TanStack Router/TanStack Query/shadcn, with a Linear-style sidebar layout and split-view terminal.

**Architecture:** Feature-based folder structure under `src/features/` with shared utilities in `src/shared/`. TanStack Router handles file-based routing under `src/routes/`. TanStack Query manages all server state with per-feature hooks. shadcn/ui provides the component library on top of Tailwind CSS v4.

**Tech Stack:** TypeScript, React 19, Vite, TanStack Router, TanStack Query, shadcn/ui, Radix UI, Tailwind CSS v4, xterm.js, react-markdown, lucide-react, sonner

**Spec:** `docs/superpowers/specs/2026-03-27-frontend-refactor-design.md`

---

### Task 1: Project Setup — TypeScript, Dependencies, Configuration

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Rename: `frontend/vite.config.js` → `frontend/vite.config.ts`
- Create: `frontend/components.json` (shadcn config)
- Modify: `frontend/src/index.css`
- Create: `frontend/src/shared/lib/utils.ts`

- [ ] **Step 1: Remove old dependencies and install new ones**

```bash
cd frontend
npm uninstall react-router-dom
npm install @tanstack/react-router @tanstack/react-query sonner lucide-react class-variance-authority clsx tailwind-merge
npm install -D @tanstack/router-plugin @tanstack/router-devtools typescript @types/node
```

- [ ] **Step 2: Create TypeScript configuration**

`frontend/tsconfig.json`:
```json
{
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ],
  "files": []
}
```

`frontend/tsconfig.app.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

`frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Create Vite config with TanStack Router plugin and path aliases**

`frontend/vite.config.ts`:
```typescript
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import { defineConfig } from "vite";
import path from "path";

const backendProxy = {
  "/api": {
    target: process.env.BACKEND_URL || "http://localhost:8000",
    changeOrigin: true,
    ws: true,
  },
};

export default defineConfig({
  plugins: [TanStackRouterVite({ quoteStyle: "double" }), react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true,
    proxy: backendProxy,
  },
  preview: {
    host: true,
    proxy: backendProxy,
  },
});
```

- [ ] **Step 4: Create shadcn components.json config**

`frontend/components.json`:
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/index.css",
    "baseColor": "zinc",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/shared/components",
    "utils": "@/shared/lib/utils",
    "ui": "@/shared/components/ui",
    "lib": "@/shared/lib",
    "hooks": "@/shared/hooks"
  },
  "iconLibrary": "lucide"
}
```

- [ ] **Step 5: Create the cn() utility**

`frontend/src/shared/lib/utils.ts`:
```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 6: Update index.css with shadcn CSS variables**

`frontend/src/index.css`:
```css
@import "tailwindcss";

@custom-variant dark (&:is(.dark *));

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --destructive-foreground: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
  --radius: 0.625rem;
  --sidebar-background: oklch(0.985 0 0);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: oklch(0.205 0 0);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.97 0 0);
  --sidebar-accent-foreground: oklch(0.205 0 0);
  --sidebar-border: oklch(0.922 0 0);
  --sidebar-ring: oklch(0.708 0 0);
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --radius: var(--radius);
  --color-sidebar-background: var(--sidebar-background);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 7: Delete old vite.config.js**

```bash
cd frontend
rm vite.config.js
```

- [ ] **Step 8: Commit**

```bash
git add -A frontend/tsconfig*.json frontend/vite.config.ts frontend/components.json frontend/package.json frontend/package-lock.json frontend/src/index.css frontend/src/shared/lib/utils.ts
git commit -m "feat: setup TypeScript, TanStack Router, shadcn/ui configuration"
```

---

### Task 2: Install shadcn UI Components

**Files:**
- Create: `frontend/src/shared/components/ui/button.tsx`
- Create: `frontend/src/shared/components/ui/input.tsx`
- Create: `frontend/src/shared/components/ui/textarea.tsx`
- Create: `frontend/src/shared/components/ui/badge.tsx`
- Create: `frontend/src/shared/components/ui/card.tsx`
- Create: `frontend/src/shared/components/ui/dialog.tsx`
- Create: `frontend/src/shared/components/ui/select.tsx`
- Create: `frontend/src/shared/components/ui/dropdown-menu.tsx`
- Create: `frontend/src/shared/components/ui/separator.tsx`
- Create: `frontend/src/shared/components/ui/scroll-area.tsx`
- Create: `frontend/src/shared/components/ui/tooltip.tsx`
- Create: `frontend/src/shared/components/ui/skeleton.tsx`
- Create: `frontend/src/shared/components/ui/collapsible.tsx`
- Create: `frontend/src/shared/components/ui/sonner.tsx`
- Create: `frontend/src/shared/components/ui/resizable.tsx`
- Create: `frontend/src/shared/components/ui/sidebar.tsx`

- [ ] **Step 1: Install all shadcn components via CLI**

Run each command from the `frontend/` directory:

```bash
cd frontend
npx shadcn@latest init -y
npx shadcn@latest add button input textarea badge card dialog select dropdown-menu separator scroll-area tooltip skeleton collapsible sonner resizable sidebar -y
```

Note: If shadcn CLI places files in `src/components/ui/`, move them to `src/shared/components/ui/`. The `components.json` aliases should handle this, but verify the output paths.

- [ ] **Step 2: Verify all UI component files exist**

```bash
ls frontend/src/shared/components/ui/
```

Expected: all component files listed above.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/shared/components/ui/
git commit -m "feat: install shadcn UI components"
```

---

### Task 3: Shared Types

**Files:**
- Create: `frontend/src/shared/types/index.ts`

- [ ] **Step 1: Write all shared TypeScript types**

`frontend/src/shared/types/index.ts`:
```typescript
// ── Issue ──

export type IssueStatus =
  | "New"
  | "Reasoning"
  | "Planned"
  | "Accepted"
  | "Finished"
  | "Canceled";

export interface Issue {
  id: string;
  project_id: string;
  name: string | null;
  description: string;
  status: IssueStatus;
  priority: number;
  plan: string | null;
  specification: string | null;
  recap: string | null;
  tasks: Task[];
  created_at: string;
  updated_at: string;
}

export interface IssueCreate {
  description: string;
  priority?: number;
}

export interface IssueUpdate {
  description?: string;
  priority?: number;
}

export interface IssueStatusUpdate {
  status: IssueStatus;
}

// ── Task ──

export type TaskStatus = "Pending" | "In Progress" | "Completed";

export interface Task {
  id: string;
  issue_id: string;
  name: string;
  status: TaskStatus;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  name: string;
}

export interface TaskUpdate {
  name?: string;
  status?: TaskStatus;
}

// ── Project ──

export interface Project {
  id: string;
  name: string;
  path: string;
  description: string;
  tech_stack: string;
  created_at: string;
  updated_at: string;
  issue_counts?: Record<string, number>;
}

export interface ProjectCreate {
  name: string;
  path: string;
  description?: string;
  tech_stack?: string;
}

export interface ProjectUpdate {
  name?: string;
  path?: string;
  description?: string | null;
  tech_stack?: string | null;
}

// ── Setting ──

export interface Setting {
  key: string;
  value: string;
  default: string;
  is_customized: boolean;
}

export interface SettingUpdate {
  value: string;
}

// ── Terminal ──

export interface Terminal {
  id: string;
  issue_id: string;
  project_id: string;
  project_path: string;
  status: string;
  created_at: string;
  cols: number;
  rows: number;
}

export interface TerminalListItem {
  id: string;
  issue_id: string;
  project_id: string;
  project_path: string;
  issue_name: string | null;
  project_name: string | null;
  status: string;
  created_at: string;
}

export interface TerminalCreate {
  issue_id: string;
  project_id: string;
}

// ── Terminal Command ──

export interface TerminalCommand {
  id: number;
  command: string;
  sort_order: number;
  project_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface TerminalCommandCreate {
  command: string;
  sort_order: number;
  project_id?: string | null;
}

export interface TerminalCommandUpdate {
  command?: string;
  sort_order?: number;
}

export interface TerminalCommandVariable {
  name: string;
  description: string;
}

// ── Project File ──

export interface ProjectFile {
  id: string;
  project_id: string;
  original_name: string;
  stored_name: string;
  file_type: string;
  file_size: number;
  mime_type: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface AllowedFormats {
  accept: string;
  extensions: string[];
  label: string;
}

// ── Event ──

export interface ServerEvent {
  [key: string]: unknown;
  issue_id?: string;
  project_id?: string;
  issue_name?: string;
  timestamp?: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/shared/types/index.ts
git commit -m "feat: add shared TypeScript type definitions"
```

---

### Task 4: API Client Base

**Files:**
- Create: `frontend/src/shared/api/client.ts`

- [ ] **Step 1: Write the typed API client**

`frontend/src/shared/api/client.ts`:
```typescript
const BASE = "/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (res.status === 204) return null as T;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(err.detail || "Request failed", res.status);
  }
  return res.json();
}

export async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(err.detail || "Upload failed", res.status);
  }
  return res.json();
}

export function buildUrl(path: string): string {
  return `${BASE}${path}`;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/shared/api/client.ts
git commit -m "feat: add typed API client base"
```

---

### Task 5: Feature API Layers

**Files:**
- Create: `frontend/src/features/projects/api.ts`
- Create: `frontend/src/features/issues/api.ts`
- Create: `frontend/src/features/terminals/api.ts`
- Create: `frontend/src/features/files/api.ts`
- Create: `frontend/src/features/settings/api.ts`

- [ ] **Step 1: Write projects API**

`frontend/src/features/projects/api.ts`:
```typescript
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
```

- [ ] **Step 2: Write issues API**

`frontend/src/features/issues/api.ts`:
```typescript
import { request } from "@/shared/api/client";
import type {
  Issue,
  IssueCreate,
  IssueStatus,
  IssueStatusUpdate,
  IssueUpdate,
  Task,
  TaskCreate,
  TaskUpdate,
} from "@/shared/types";

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
  return request(`/projects/${projectId}/issues/${issueId}/tasks`, {
    method: "POST",
    body: JSON.stringify({ tasks }),
  });
}

export function replaceTasks(projectId: string, issueId: string, tasks: TaskCreate[]): Promise<Task[]> {
  return request(`/projects/${projectId}/issues/${issueId}/tasks`, {
    method: "PUT",
    body: JSON.stringify({ tasks }),
  });
}

export function updateTask(projectId: string, issueId: string, taskId: string, data: TaskUpdate): Promise<Task> {
  return request(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteTask(projectId: string, issueId: string, taskId: string): Promise<null> {
  return request(`/projects/${projectId}/issues/${issueId}/tasks/${taskId}`, { method: "DELETE" });
}
```

- [ ] **Step 3: Write terminals API**

`frontend/src/features/terminals/api.ts`:
```typescript
import { request } from "@/shared/api/client";
import type {
  Terminal,
  TerminalCommand,
  TerminalCommandCreate,
  TerminalCommandUpdate,
  TerminalCommandVariable,
  TerminalCreate,
  TerminalListItem,
} from "@/shared/types";

export function fetchTerminals(projectId?: string, issueId?: string): Promise<TerminalListItem[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (issueId) params.set("issue_id", issueId);
  const qs = params.toString();
  return request(`/terminals${qs ? `?${qs}` : ""}`);
}

export function createTerminal(data: TerminalCreate): Promise<Terminal> {
  return request("/terminals", { method: "POST", body: JSON.stringify(data) });
}

export function killTerminal(terminalId: string): Promise<null> {
  return request(`/terminals/${terminalId}`, { method: "DELETE" });
}

export function fetchTerminalCount(): Promise<{ count: number }> {
  return request("/terminals/count");
}

export function fetchTerminalConfig(): Promise<{ soft_limit: number }> {
  return request("/terminals/config");
}

// ── Terminal Commands ──

export function fetchTerminalCommandVariables(): Promise<TerminalCommandVariable[]> {
  return request("/terminal-commands/variables");
}

export function fetchTerminalCommands(projectId?: string | null): Promise<TerminalCommand[]> {
  const params = projectId != null ? `?project_id=${projectId}` : "";
  return request(`/terminal-commands${params}`);
}

export function createTerminalCommand(data: TerminalCommandCreate): Promise<TerminalCommand> {
  return request("/terminal-commands", { method: "POST", body: JSON.stringify(data) });
}

export function updateTerminalCommand(id: number, data: TerminalCommandUpdate): Promise<TerminalCommand> {
  return request(`/terminal-commands/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export function reorderTerminalCommands(commands: { id: number; sort_order: number }[]): Promise<TerminalCommand[]> {
  return request("/terminal-commands/reorder", { method: "PUT", body: JSON.stringify({ commands }) });
}

export function deleteTerminalCommand(id: number): Promise<null> {
  return request(`/terminal-commands/${id}`, { method: "DELETE" });
}
```

- [ ] **Step 4: Write files API**

`frontend/src/features/files/api.ts`:
```typescript
import { buildUrl, request, uploadRequest } from "@/shared/api/client";
import type { AllowedFormats, ProjectFile } from "@/shared/types";

export function fetchAllowedFormats(): Promise<AllowedFormats> {
  return request("/files/allowed-formats");
}

export function fetchFiles(projectId: string): Promise<ProjectFile[]> {
  return request(`/projects/${projectId}/files`);
}

export function uploadFiles(projectId: string, formData: FormData): Promise<ProjectFile[]> {
  return uploadRequest(`/projects/${projectId}/files`, formData);
}

export function getFileDownloadUrl(projectId: string, fileId: string): string {
  return buildUrl(`/projects/${projectId}/files/${fileId}/download`);
}

export function deleteFile(projectId: string, fileId: string): Promise<null> {
  return request(`/projects/${projectId}/files/${fileId}`, { method: "DELETE" });
}
```

- [ ] **Step 5: Write settings API**

`frontend/src/features/settings/api.ts`:
```typescript
import { request } from "@/shared/api/client";
import type { Setting } from "@/shared/types";

export function fetchSettings(): Promise<Setting[]> {
  return request("/settings");
}

export function updateSetting(key: string, value: string): Promise<Setting> {
  return request(`/settings/${encodeURIComponent(key)}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}

export function resetSetting(key: string): Promise<null> {
  return request(`/settings/${encodeURIComponent(key)}`, { method: "DELETE" });
}

export function resetAllSettings(): Promise<null> {
  return request("/settings", { method: "DELETE" });
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/
git commit -m "feat: add typed API layers for all features"
```

---

### Task 6: TanStack Query Setup and Feature Hooks

**Files:**
- Create: `frontend/src/shared/lib/query-client.ts`
- Create: `frontend/src/features/projects/hooks.ts`
- Create: `frontend/src/features/issues/hooks.ts`
- Create: `frontend/src/features/terminals/hooks.ts`
- Create: `frontend/src/features/files/hooks.ts`
- Create: `frontend/src/features/settings/hooks.ts`

- [ ] **Step 1: Create query client instance**

`frontend/src/shared/lib/query-client.ts`:
```typescript
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});
```

- [ ] **Step 2: Write projects hooks**

`frontend/src/features/projects/hooks.ts`:
```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { ProjectCreate, ProjectUpdate } from "@/shared/types";

export const projectKeys = {
  all: ["projects"] as const,
  detail: (id: string) => ["projects", id] as const,
};

export function useProjects() {
  return useQuery({
    queryKey: projectKeys.all,
    queryFn: api.fetchProjects,
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => api.fetchProject(projectId),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectCreate) => api.createProject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectUpdate) => api.updateProject(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useInstallManagerJson(projectId: string) {
  return useMutation({
    mutationFn: () => api.installManagerJson(projectId),
  });
}

export function useInstallClaudeResources(projectId: string) {
  return useMutation({
    mutationFn: () => api.installClaudeResources(projectId),
  });
}
```

- [ ] **Step 3: Write issues hooks**

`frontend/src/features/issues/hooks.ts`:
```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { IssueCreate, IssueStatus, IssueStatusUpdate, IssueUpdate } from "@/shared/types";

export const issueKeys = {
  all: (projectId: string) => ["projects", projectId, "issues"] as const,
  detail: (projectId: string, issueId: string) => ["projects", projectId, "issues", issueId] as const,
  tasks: (projectId: string, issueId: string) => ["projects", projectId, "issues", issueId, "tasks"] as const,
};

export function useIssues(projectId: string, status?: IssueStatus) {
  return useQuery({
    queryKey: [...issueKeys.all(projectId), status] as const,
    queryFn: () => api.fetchIssues(projectId, status),
  });
}

export function useIssue(projectId: string, issueId: string) {
  return useQuery({
    queryKey: issueKeys.detail(projectId, issueId),
    queryFn: () => api.fetchIssue(projectId, issueId),
  });
}

export function useCreateIssue(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueCreate) => api.createIssue(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useUpdateIssue(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueUpdate) => api.updateIssue(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useUpdateIssueStatus(projectId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueStatusUpdate) => api.updateIssueStatus(projectId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.detail(projectId, issueId) });
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}

export function useDeleteIssue(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (issueId: string) => api.deleteIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
  });
}
```

- [ ] **Step 4: Write terminals hooks**

`frontend/src/features/terminals/hooks.ts`:
```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { TerminalCreate } from "@/shared/types";

export const terminalKeys = {
  all: ["terminals"] as const,
  count: ["terminals", "count"] as const,
  config: ["terminals", "config"] as const,
  commands: (projectId?: string | null) => ["terminal-commands", projectId] as const,
  variables: ["terminal-commands", "variables"] as const,
};

export function useTerminals(projectId?: string, issueId?: string) {
  return useQuery({
    queryKey: [...terminalKeys.all, projectId, issueId] as const,
    queryFn: () => api.fetchTerminals(projectId, issueId),
  });
}

export function useTerminalCount() {
  return useQuery({
    queryKey: terminalKeys.count,
    queryFn: api.fetchTerminalCount,
    refetchInterval: 5_000,
  });
}

export function useTerminalConfig() {
  return useQuery({
    queryKey: terminalKeys.config,
    queryFn: api.fetchTerminalConfig,
    staleTime: Infinity,
  });
}

export function useCreateTerminal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TerminalCreate) => api.createTerminal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.all });
      queryClient.invalidateQueries({ queryKey: terminalKeys.count });
    },
  });
}

export function useKillTerminal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (terminalId: string) => api.killTerminal(terminalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.all });
      queryClient.invalidateQueries({ queryKey: terminalKeys.count });
    },
  });
}

// ── Terminal Commands ──

export function useTerminalCommands(projectId?: string | null) {
  return useQuery({
    queryKey: terminalKeys.commands(projectId),
    queryFn: () => api.fetchTerminalCommands(projectId),
  });
}

export function useTerminalCommandVariables() {
  return useQuery({
    queryKey: terminalKeys.variables,
    queryFn: api.fetchTerminalCommandVariables,
    staleTime: Infinity,
  });
}

export function useCreateTerminalCommand(projectId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createTerminalCommand,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.commands(projectId) });
    },
  });
}

export function useUpdateTerminalCommand(projectId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { command?: string; sort_order?: number } }) =>
      api.updateTerminalCommand(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.commands(projectId) });
    },
  });
}

export function useReorderTerminalCommands(projectId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (commands: { id: number; sort_order: number }[]) => api.reorderTerminalCommands(commands),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.commands(projectId) });
    },
  });
}

export function useDeleteTerminalCommand(projectId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteTerminalCommand(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.commands(projectId) });
    },
  });
}
```

- [ ] **Step 5: Write files hooks**

`frontend/src/features/files/hooks.ts`:
```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

export const fileKeys = {
  all: (projectId: string) => ["projects", projectId, "files"] as const,
  formats: ["files", "allowed-formats"] as const,
};

export function useFiles(projectId: string) {
  return useQuery({
    queryKey: fileKeys.all(projectId),
    queryFn: () => api.fetchFiles(projectId),
  });
}

export function useAllowedFormats() {
  return useQuery({
    queryKey: fileKeys.formats,
    queryFn: api.fetchAllowedFormats,
    staleTime: Infinity,
  });
}

export function useUploadFiles(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => api.uploadFiles(projectId, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fileKeys.all(projectId) });
    },
  });
}

export function useDeleteFile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fileId: string) => api.deleteFile(projectId, fileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fileKeys.all(projectId) });
    },
  });
}
```

- [ ] **Step 6: Write settings hooks**

`frontend/src/features/settings/hooks.ts`:
```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

export const settingKeys = {
  all: ["settings"] as const,
};

export function useSettings() {
  return useQuery({
    queryKey: settingKeys.all,
    queryFn: api.fetchSettings,
  });
}

export function useUpdateSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => api.updateSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingKeys.all });
    },
  });
}

export function useResetSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => api.resetSetting(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingKeys.all });
    },
  });
}

export function useResetAllSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.resetAllSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingKeys.all });
    },
  });
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/shared/lib/query-client.ts frontend/src/features/
git commit -m "feat: add TanStack Query client and feature hooks"
```

---

### Task 7: Event Context with Query Invalidation and Sonner

**Files:**
- Create: `frontend/src/shared/context/event-context.tsx`

- [ ] **Step 1: Write event context with WebSocket + query invalidation + sonner toasts**

`frontend/src/shared/context/event-context.tsx`:
```typescript
import { createContext, useCallback, useContext, useEffect, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { queryClient } from "@/shared/lib/query-client";

interface EventContextValue {
  // Extensible if needed in the future
}

const EventContext = createContext<EventContextValue | null>(null);

const notificationAudio = new Audio("/sounds/notification.wav");
notificationAudio.volume = 0.5;

function unlockAudio() {
  notificationAudio
    .play()
    .then(() => {
      notificationAudio.pause();
      notificationAudio.currentTime = 0;
    })
    .catch(() => {});
  document.removeEventListener("click", unlockAudio);
  document.removeEventListener("keydown", unlockAudio);
}
document.addEventListener("click", unlockAudio);
document.addEventListener("keydown", unlockAudio);

function playNotificationSound() {
  try {
    notificationAudio.currentTime = 0;
    notificationAudio.play().catch(() => {});
  } catch {
    // Audio API unavailable
  }
}

export function EventProvider({ children }: { children: React.ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const backoffRef = useRef(1000);
  const cleanedUpRef = useRef(false);
  const navigate = useNavigate();

  const connect = useCallback(() => {
    if (cleanedUpRef.current) return;

    const backendPort = import.meta.env.VITE_BACKEND_PORT || "8000";
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.hostname}:${backendPort}/api/events/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (cleanedUpRef.current) {
        ws.close();
        return;
      }
      backoffRef.current = 1000;
    };

    ws.onmessage = (event) => {
      if (cleanedUpRef.current) return;
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;
        const projectId = data.project_id as string | undefined;
        const issueId = data.issue_id as string | undefined;
        const issueName = data.issue_name as string | undefined;
        const message =
          (data.message as string) || (data.status as string) || "New event";

        toast(issueName || "Event", {
          description: message,
          action: projectId && issueId
            ? {
                label: "View",
                onClick: () => {
                  navigate({
                    to: "/projects/$projectId/issues/$issueId",
                    params: { projectId, issueId },
                  });
                },
              }
            : undefined,
        });

        playNotificationSound();

        // Invalidate relevant queries for real-time updates
        if (projectId && issueId) {
          queryClient.invalidateQueries({
            queryKey: ["projects", projectId, "issues", issueId],
          });
          queryClient.invalidateQueries({
            queryKey: ["projects", projectId, "issues"],
          });
        } else if (projectId) {
          queryClient.invalidateQueries({
            queryKey: ["projects", projectId],
          });
        }
      } catch {
        // Ignore unparseable messages
      }
    };

    ws.onclose = () => {
      if (cleanedUpRef.current) return;
      const delay = Math.min(backoffRef.current, 30000);
      backoffRef.current = Math.min(backoffRef.current * 2, 30000);
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [navigate]);

  useEffect(() => {
    cleanedUpRef.current = false;
    connect();

    return () => {
      cleanedUpRef.current = true;
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close();
        }
        wsRef.current = null;
      }
    };
  }, [connect]);

  return (
    <EventContext.Provider value={{}}>
      {children}
    </EventContext.Provider>
  );
}

export function useEvents() {
  return useContext(EventContext);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/shared/context/event-context.tsx
git commit -m "feat: add event context with WebSocket, query invalidation, and sonner toasts"
```

---

### Task 8: Shared Components — Markdown Viewer and Status Badge

**Files:**
- Create: `frontend/src/shared/components/markdown-viewer.tsx`
- Create: `frontend/src/features/issues/components/status-badge.tsx`

- [ ] **Step 1: Write markdown viewer**

`frontend/src/shared/components/markdown-viewer.tsx`:
```typescript
import ReactMarkdown from "react-markdown";

interface MarkdownViewerProps {
  content: string | null;
}

export function MarkdownViewer({ content }: MarkdownViewerProps) {
  if (!content) return <p className="text-muted-foreground italic text-sm">No content</p>;
  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 2: Write status badge using shadcn Badge**

`frontend/src/features/issues/components/status-badge.tsx`:
```typescript
import { Badge } from "@/shared/components/ui/badge";
import type { IssueStatus, TaskStatus } from "@/shared/types";

const STATUS_VARIANTS: Record<string, string> = {
  // Issue statuses
  New: "bg-blue-100 text-blue-800 hover:bg-blue-100",
  Reasoning: "bg-indigo-100 text-indigo-800 hover:bg-indigo-100",
  Planned: "bg-yellow-100 text-yellow-800 hover:bg-yellow-100",
  Accepted: "bg-green-100 text-green-800 hover:bg-green-100",
  Finished: "bg-zinc-100 text-zinc-800 hover:bg-zinc-100",
  Canceled: "bg-zinc-100 text-zinc-500 hover:bg-zinc-100",
  // Task statuses
  Pending: "bg-slate-100 text-slate-700 hover:bg-slate-100",
  "In Progress": "bg-amber-100 text-amber-800 hover:bg-amber-100",
  Completed: "bg-emerald-100 text-emerald-800 hover:bg-emerald-100",
};

interface StatusBadgeProps {
  status: IssueStatus | TaskStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge variant="secondary" className={STATUS_VARIANTS[status] || ""}>
      {status}
    </Badge>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/shared/components/markdown-viewer.tsx frontend/src/features/issues/components/status-badge.tsx
git commit -m "feat: add markdown viewer and status badge components"
```

---

### Task 9: App Sidebar Component

**Files:**
- Create: `frontend/src/shared/components/app-sidebar.tsx`
- Create: `frontend/src/features/projects/components/project-switcher.tsx`

- [ ] **Step 1: Write project switcher**

`frontend/src/features/projects/components/project-switcher.tsx`:
```typescript
import { ChevronsUpDown, FolderKanban, Plus } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu";
import { SidebarMenuButton } from "@/shared/components/ui/sidebar";
import { useProjects } from "@/features/projects/hooks";
import type { Project } from "@/shared/types";

interface ProjectSwitcherProps {
  activeProject: Project | null;
}

export function ProjectSwitcher({ activeProject }: ProjectSwitcherProps) {
  const navigate = useNavigate();
  const { data: projects } = useProjects();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <SidebarMenuButton
          size="lg"
          className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
        >
          <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <FolderKanban className="size-4" />
          </div>
          <div className="grid flex-1 text-left text-sm leading-tight">
            <span className="truncate font-semibold">
              {activeProject?.name || "Select Project"}
            </span>
            {activeProject && (
              <span className="truncate text-xs text-muted-foreground font-mono">
                {activeProject.path}
              </span>
            )}
          </div>
          <ChevronsUpDown className="ml-auto size-4" />
        </SidebarMenuButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        className="w-[--radix-dropdown-menu-trigger-width] min-w-56"
        align="start"
        sideOffset={4}
      >
        {projects?.map((project) => (
          <DropdownMenuItem
            key={project.id}
            onClick={() =>
              navigate({
                to: "/projects/$projectId/issues",
                params: { projectId: project.id },
              })
            }
            className="gap-2"
          >
            <FolderKanban className="size-4" />
            <span className="truncate">{project.name}</span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => navigate({ to: "/projects/new" })}
          className="gap-2"
        >
          <Plus className="size-4" />
          <span>New Project</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

- [ ] **Step 2: Write app sidebar**

`frontend/src/shared/components/app-sidebar.tsx`:
```typescript
import {
  CircleDot,
  FileText,
  Settings,
  SquareTerminal,
  Terminal,
} from "lucide-react";
import { Link, useMatchRoute } from "@tanstack/react-router";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/shared/components/ui/sidebar";
import { ProjectSwitcher } from "@/features/projects/components/project-switcher";
import { useTerminalCount } from "@/features/terminals/hooks";
import type { Project } from "@/shared/types";

interface AppSidebarProps {
  activeProject: Project | null;
}

export function AppSidebar({ activeProject }: AppSidebarProps) {
  const { data: countData } = useTerminalCount();
  const terminalCount = countData?.count ?? 0;
  const matchRoute = useMatchRoute();

  const projectId = activeProject?.id;

  const projectNav = projectId
    ? [
        {
          label: "Issues",
          to: "/projects/$projectId/issues" as const,
          params: { projectId },
          icon: CircleDot,
        },
        {
          label: "Files",
          to: "/projects/$projectId/files" as const,
          params: { projectId },
          icon: FileText,
        },
        {
          label: "Commands",
          to: "/projects/$projectId/commands" as const,
          params: { projectId },
          icon: SquareTerminal,
        },
      ]
    : [];

  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <ProjectSwitcher activeProject={activeProject} />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {projectId && (
          <SidebarGroup>
            <SidebarGroupLabel>Project</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {projectNav.map((item) => (
                  <SidebarMenuItem key={item.label}>
                    <SidebarMenuButton
                      asChild
                      isActive={!!matchRoute({ to: item.to, params: item.params, fuzzy: true })}
                    >
                      <Link to={item.to} params={item.params}>
                        <item.icon />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        <SidebarSeparator />

        <SidebarGroup>
          <SidebarGroupLabel>Global</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={!!matchRoute({ to: "/terminals", fuzzy: true })}
                >
                  <Link to="/terminals">
                    <Terminal />
                    <span>Terminals</span>
                  </Link>
                </SidebarMenuButton>
                {terminalCount > 0 && (
                  <SidebarMenuBadge>{terminalCount}</SidebarMenuBadge>
                )}
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={!!matchRoute({ to: "/settings", fuzzy: true })}
                >
                  <Link to="/settings">
                    <Settings />
                    <span>Settings</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild size="sm">
              <span className="text-xs text-muted-foreground">Manager AI</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/shared/components/app-sidebar.tsx frontend/src/features/projects/components/project-switcher.tsx
git commit -m "feat: add app sidebar with project switcher and navigation"
```

---

### Task 10: TanStack Router — Root Layout and Entry Point

**Files:**
- Create: `frontend/src/routes/__root.tsx`
- Create: `frontend/src/routes/index.tsx`
- Rewrite: `frontend/src/main.tsx` (rename from main.jsx)

- [ ] **Step 1: Write root layout route**

`frontend/src/routes/__root.tsx`:
```typescript
import { createRootRoute, Outlet } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { queryClient } from "@/shared/lib/query-client";
import { SidebarInset, SidebarProvider } from "@/shared/components/ui/sidebar";
import { AppSidebar } from "@/shared/components/app-sidebar";
import { EventProvider } from "@/shared/context/event-context";
import { useProject } from "@/features/projects/hooks";

function RootComponent() {
  return (
    <QueryClientProvider client={queryClient}>
      <EventProvider>
        <RootLayout />
        <Toaster position="bottom-right" richColors closeButton />
      </EventProvider>
    </QueryClientProvider>
  );
}

function RootLayout() {
  // Try to extract projectId from URL to show active project in sidebar
  const projectId = extractProjectIdFromUrl();
  const projectQuery = useProject(projectId ?? "");
  const activeProject = projectId ? (projectQuery.data ?? null) : null;

  return (
    <SidebarProvider>
      <AppSidebar activeProject={activeProject} />
      <SidebarInset>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

function extractProjectIdFromUrl(): string | null {
  const match = window.location.pathname.match(/\/projects\/([^/]+)/);
  return match?.[1] ?? null;
}

export const Route = createRootRoute({
  component: RootComponent,
});
```

- [ ] **Step 2: Write index route (project list / redirect)**

`frontend/src/routes/index.tsx`:
```typescript
import { createFileRoute, Link } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useProjects } from "@/features/projects/hooks";
import { Button } from "@/shared/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { StatusBadge } from "@/features/issues/components/status-badge";
import type { IssueStatus } from "@/shared/types";

export const Route = createFileRoute("/")({
  component: ProjectsPage,
});

function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <Button asChild>
          <Link to="/">
            <Plus className="size-4 mr-2" />
            New Project
          </Link>
        </Button>
      </div>

      {!projects || projects.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">No projects yet.</p>
          <Button asChild variant="outline">
            <Link to="/">Create your first project</Link>
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {projects.map((project) => {
            const counts = project.issue_counts || {};
            const total = Object.values(counts).reduce((a, b) => a + b, 0);
            return (
              <Link
                key={project.id}
                to="/projects/$projectId/issues"
                params={{ projectId: project.id }}
              >
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardHeader>
                    <CardTitle>{project.name}</CardTitle>
                    <CardDescription className="font-mono text-xs">
                      {project.path}
                    </CardDescription>
                    {project.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                        {project.description}
                      </p>
                    )}
                    {total > 0 && (
                      <div className="flex gap-2 mt-2 flex-wrap">
                        {Object.entries(counts).map(([status, count]) => (
                          <span key={status} className="flex items-center gap-1 text-xs">
                            <StatusBadge status={status as IssueStatus} /> {count}
                          </span>
                        ))}
                      </div>
                    )}
                  </CardHeader>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Write main entry point**

Delete `frontend/src/main.jsx` and `frontend/src/App.jsx`, then create `frontend/src/main.tsx`:

```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";
import "./index.css";

const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
```

- [ ] **Step 4: Update index.html to reference main.tsx**

In `frontend/index.html`, change:
```html
<script type="module" src="/src/main.jsx"></script>
```
to:
```html
<script type="module" src="/src/main.tsx"></script>
```

- [ ] **Step 5: Delete old JS files**

```bash
cd frontend/src
rm -f main.jsx App.jsx
```

- [ ] **Step 6: Generate route tree and verify app starts**

```bash
cd frontend
npx tsr generate
npm run dev
```

Verify the dev server starts without errors and the home page renders.

- [ ] **Step 7: Commit**

```bash
git add -A frontend/
git commit -m "feat: add TanStack Router root layout, entry point, and projects index page"
```

---

### Task 11: Project Layout Route

**Files:**
- Create: `frontend/src/routes/projects/$projectId.tsx`
- Create: `frontend/src/features/projects/components/project-settings-dialog.tsx`

- [ ] **Step 1: Write project settings dialog**

`frontend/src/features/projects/components/project-settings-dialog.tsx`:
```typescript
import { useState } from "react";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";
import { useUpdateProject } from "@/features/projects/hooks";
import type { Project } from "@/shared/types";

interface ProjectSettingsDialogProps {
  project: Project;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProjectSettingsDialog({
  project,
  open,
  onOpenChange,
}: ProjectSettingsDialogProps) {
  const [form, setForm] = useState({
    name: project.name,
    path: project.path,
    description: project.description || "",
    tech_stack: project.tech_stack || "",
  });

  const updateProject = useUpdateProject(project.id);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateProject.mutate(form, {
      onSuccess: () => onOpenChange(false),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Project</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium">Name</label>
            <Input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Path</label>
            <Input
              required
              value={form.path}
              onChange={(e) => setForm({ ...form, path: e.target.value })}
              className="font-mono"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Description</label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Tech Stack</label>
            <Textarea
              value={form.tech_stack}
              onChange={(e) => setForm({ ...form, tech_stack: e.target.value })}
              rows={3}
            />
          </div>
          {updateProject.error && (
            <p className="text-sm text-destructive">{updateProject.error.message}</p>
          )}
          <div className="flex gap-3 justify-end">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={updateProject.isPending}>
              {updateProject.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Write project layout route**

`frontend/src/routes/projects/$projectId.tsx`:
```typescript
import { createFileRoute, Outlet } from "@tanstack/react-router";
import { useProject } from "@/features/projects/hooks";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/$projectId")({
  component: ProjectLayout,
});

function ProjectLayout() {
  const { projectId } = Route.useParams();
  const { data: project, isLoading, error } = useProject(projectId);

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="p-6">
        <p className="text-destructive">Project not found.</p>
      </div>
    );
  }

  return <Outlet />;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/projects/ frontend/src/features/projects/components/project-settings-dialog.tsx
git commit -m "feat: add project layout route and settings dialog"
```

---

### Task 12: Issues List Route

**Files:**
- Create: `frontend/src/routes/projects/$projectId/issues.tsx`
- Create: `frontend/src/features/issues/components/issue-list.tsx`

- [ ] **Step 1: Write issue list component**

`frontend/src/features/issues/components/issue-list.tsx`:
```typescript
import { Link } from "@tanstack/react-router";
import { StatusBadge } from "./status-badge";
import type { Issue } from "@/shared/types";

interface IssueListProps {
  issues: Issue[];
  projectId: string;
  activeTerminalIssueIds: string[];
}

export function IssueList({ issues, projectId, activeTerminalIssueIds }: IssueListProps) {
  if (issues.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No issues yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {issues.map((issue) => {
        const hasTerminal = activeTerminalIssueIds.includes(issue.id);
        return (
          <Link
            key={issue.id}
            to="/projects/$projectId/issues/$issueId"
            params={{ projectId, issueId: issue.id }}
            className="flex items-center justify-between rounded-md border px-4 py-3 hover:bg-accent transition-colors"
          >
            <div className="flex items-center flex-1 min-w-0">
              {hasTerminal && (
                <span
                  className="w-2 h-2 rounded-full bg-green-400 mr-3 flex-shrink-0"
                  style={{ boxShadow: "0 0 6px #4ade80" }}
                  title="Terminal active"
                />
              )}
              <div className="min-w-0">
                <p className="font-medium truncate">
                  {issue.name || issue.description}
                </p>
                {issue.name && (
                  <p className="text-sm text-muted-foreground truncate">
                    {issue.description}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3 ml-4">
              <span className="text-sm text-muted-foreground">P{issue.priority}</span>
              <StatusBadge status={issue.status} />
            </div>
          </Link>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Write issues list route**

`frontend/src/routes/projects/$projectId/issues.tsx`:
```typescript
import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useIssues } from "@/features/issues/hooks";
import { useTerminals } from "@/features/terminals/hooks";
import { IssueList } from "@/features/issues/components/issue-list";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import type { IssueStatus } from "@/shared/types";

const STATUSES: Array<IssueStatus | "All"> = [
  "All",
  "New",
  "Reasoning",
  "Planned",
  "Accepted",
  "Finished",
  "Canceled",
];

export const Route = createFileRoute("/projects/$projectId/issues")({
  component: IssuesPage,
});

function IssuesPage() {
  const { projectId } = Route.useParams();
  const [filter, setFilter] = useState<IssueStatus | "All">("All");

  const { data: issues, isLoading } = useIssues(
    projectId,
    filter === "All" ? undefined : filter,
  );
  const { data: terminals } = useTerminals(projectId);

  const activeTerminalIssueIds = terminals?.map((t) => t.issue_id) ?? [];

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-semibold">Issues</h1>
        <Button asChild size="sm">
          <Link
            to="/projects/$projectId/issues/new"
            params={{ projectId }}
          >
            <Plus className="size-4 mr-1" />
            New Issue
          </Link>
        </Button>
      </div>

      <div className="flex gap-1.5 mb-4 flex-wrap">
        {STATUSES.map((s) => (
          <Button
            key={s}
            variant={filter === s ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(s)}
            className="text-xs"
          >
            {s}
          </Button>
        ))}
      </div>

      <IssueList
        issues={issues ?? []}
        projectId={projectId}
        activeTerminalIssueIds={activeTerminalIssueIds}
      />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/projects/$projectId/issues.tsx frontend/src/features/issues/components/issue-list.tsx
git commit -m "feat: add issues list route with status filters"
```

---

### Task 13: Issue Detail Route with Split-View Terminal

**Files:**
- Create: `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`
- Create: `frontend/src/features/issues/components/issue-detail.tsx`
- Create: `frontend/src/features/issues/components/task-list.tsx`
- Create: `frontend/src/features/terminals/components/terminal-panel.tsx`

- [ ] **Step 1: Write task list component**

`frontend/src/features/issues/components/task-list.tsx`:
```typescript
import { StatusBadge } from "./status-badge";
import type { Task } from "@/shared/types";

interface TaskListProps {
  tasks: Task[];
}

export function TaskList({ tasks }: TaskListProps) {
  if (tasks.length === 0) return null;

  return (
    <div className="space-y-1">
      {tasks.map((task) => (
        <div key={task.id} className="flex items-center gap-2 text-sm">
          <StatusBadge status={task.status} />
          <span>{task.name}</span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Write issue detail component (scrollable center content)**

`frontend/src/features/issues/components/issue-detail.tsx`:
```typescript
import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/shared/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { MarkdownViewer } from "@/shared/components/markdown-viewer";
import { StatusBadge } from "./status-badge";
import { TaskList } from "./task-list";
import { useDeleteIssue } from "@/features/issues/hooks";
import { useKillTerminal } from "@/features/terminals/hooks";
import type { Issue } from "@/shared/types";

interface IssueDetailProps {
  issue: Issue;
  projectId: string;
  terminalId: string | null;
}

export function IssueDetail({ issue, projectId, terminalId }: IssueDetailProps) {
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const deleteIssue = useDeleteIssue(projectId);
  const killTerminal = useKillTerminal();

  const handleDelete = async () => {
    if (terminalId) {
      try {
        await killTerminal.mutateAsync(terminalId);
      } catch {
        // Terminal may already be dead
      }
    }
    deleteIssue.mutate(issue.id, {
      onSuccess: () => {
        navigate({
          to: "/projects/$projectId/issues",
          params: { projectId },
        });
      },
    });
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-xl font-bold">{issue.name || "Untitled Issue"}</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-sm text-muted-foreground">Priority: {issue.priority}</span>
            <StatusBadge status={issue.status} />
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive"
          onClick={() => setShowDeleteConfirm(true)}
        >
          <Trash2 className="size-4 mr-1" />
          Delete
        </Button>
      </div>

      {/* Description */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold uppercase text-muted-foreground">
            Description
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">{issue.description}</p>
        </CardContent>
      </Card>

      {/* Specification */}
      {issue.specification && (
        <Collapsible defaultOpen>
          <Card>
            <CardHeader>
              <CollapsibleTrigger asChild>
                <CardTitle className="text-sm font-semibold uppercase text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                  Specification
                </CardTitle>
              </CollapsibleTrigger>
            </CardHeader>
            <CollapsibleContent>
              <CardContent>
                <MarkdownViewer content={issue.specification} />
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}

      {/* Plan */}
      {issue.plan && (
        <Collapsible defaultOpen>
          <Card>
            <CardHeader>
              <CollapsibleTrigger asChild>
                <CardTitle className="text-sm font-semibold uppercase text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                  Plan
                </CardTitle>
              </CollapsibleTrigger>
            </CardHeader>
            <CollapsibleContent>
              <CardContent>
                <MarkdownViewer content={issue.plan} />
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}

      {/* Tasks */}
      {issue.tasks && issue.tasks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold uppercase text-muted-foreground">
              Tasks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList tasks={issue.tasks} />
          </CardContent>
        </Card>
      )}

      {/* Recap */}
      {issue.recap && (
        <Collapsible defaultOpen>
          <Card>
            <CardHeader>
              <CollapsibleTrigger asChild>
                <CardTitle className="text-sm font-semibold uppercase text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                  Recap
                </CardTitle>
              </CollapsibleTrigger>
            </CardHeader>
            <CollapsibleContent>
              <CardContent>
                <MarkdownViewer content={issue.recap} />
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}

      {/* Delete confirmation */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Issue?</DialogTitle>
            <DialogDescription>
              This will permanently delete this issue and all its tasks. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteIssue.isPending}
            >
              {deleteIssue.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 3: Write terminal panel**

`frontend/src/features/terminals/components/terminal-panel.tsx`:
```typescript
import { useEffect, useRef, useState } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "xterm/css/xterm.css";

interface TerminalPanelProps {
  terminalId: string;
  onSessionEnd?: () => void;
}

export function TerminalPanel({ terminalId, onSessionEnd }: TerminalPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onSessionEndRef = useRef(onSessionEnd);
  const cleanedUpRef = useRef(false);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected" | "ended">("connecting");
  const retryCountRef = useRef(0);
  const MAX_RETRIES = 5;

  useEffect(() => {
    onSessionEndRef.current = onSessionEnd;
  }, [onSessionEnd]);

  useEffect(() => {
    if (!terminalId || !containerRef.current) return;
    cleanedUpRef.current = false;

    const container = containerRef.current;
    container.innerHTML = "";

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Cascadia Code', 'Consolas', monospace",
      theme: {
        background: "#0d0d0d",
        foreground: "#cdd6f4",
        cursor: "#89b4fa",
      },
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);

    let opened = false;

    function openIfReady() {
      if (opened || cleanedUpRef.current) return;
      if (container.clientHeight === 0 || container.clientWidth === 0) return;

      opened = true;
      try {
        term.open(container);
        fitAddon.fit();
      } catch {
        return;
      }
      connectWs();
    }

    function connectWs() {
      if (cleanedUpRef.current) return;
      const backendPort = import.meta.env.VITE_BACKEND_PORT || "8000";
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.hostname}:${backendPort}/api/terminals/${terminalId}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cleanedUpRef.current) {
          ws.close();
          return;
        }
        setStatus("connected");
        retryCountRef.current = 0;
        const dims = fitAddon.proposeDimensions();
        if (dims?.cols && dims?.rows) {
          ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      };

      ws.onmessage = (event) => {
        if (!cleanedUpRef.current) term.write(event.data);
      };

      ws.onclose = (event) => {
        if (cleanedUpRef.current) return;
        if (event.code === 1000 && event.reason === "Terminal session ended") {
          setStatus("ended");
          onSessionEndRef.current?.();
          return;
        }
        setStatus("disconnected");
        if (retryCountRef.current < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          retryCountRef.current++;
          setTimeout(connectWs, delay);
        }
      };

      ws.onerror = () => {};
    }

    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data);
      }
    });

    const resizeObserver = new ResizeObserver(() => {
      if (cleanedUpRef.current) return;
      if (!opened) {
        openIfReady();
        return;
      }
      if (container.clientHeight === 0) return;
      try {
        fitAddon.fit();
        const dims = fitAddon.proposeDimensions();
        if (dims?.cols && dims?.rows && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
        }
      } catch {
        // ignore fit errors during transitions
      }
    });
    resizeObserver.observe(container);

    openIfReady();

    return () => {
      cleanedUpRef.current = true;
      resizeObserver.disconnect();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      const termToDispose = term;
      setTimeout(() => {
        try {
          termToDispose.dispose();
        } catch {}
      }, 50);
    };
  }, [terminalId]);

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d]">
      {status === "ended" && (
        <div className="px-3 py-2 bg-zinc-800 text-zinc-400 text-sm text-center">
          Terminal session ended
        </div>
      )}
      {status === "disconnected" && (
        <div className="px-3 py-2 bg-yellow-900 text-yellow-300 text-sm text-center">
          Reconnecting...
        </div>
      )}
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  );
}
```

- [ ] **Step 4: Write issue detail route with split view**

`frontend/src/routes/projects/$projectId/issues/$issueId.tsx`:
```typescript
import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Play, Square } from "lucide-react";
import { toast } from "sonner";
import { useIssue } from "@/features/issues/hooks";
import { useTerminals, useCreateTerminal, useKillTerminal, useTerminalCount, useTerminalConfig } from "@/features/terminals/hooks";
import { IssueDetail } from "@/features/issues/components/issue-detail";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/shared/components/ui/resizable";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Skeleton } from "@/shared/components/ui/skeleton";

export const Route = createFileRoute("/projects/$projectId/issues/$issueId")({
  component: IssueDetailPage,
});

function IssueDetailPage() {
  const { projectId, issueId } = Route.useParams();
  const { data: issue, isLoading } = useIssue(projectId, issueId);
  const { data: terminals } = useTerminals(undefined, issueId);
  const createTerminal = useCreateTerminal();
  const killTerminal = useKillTerminal();
  const { data: countData } = useTerminalCount();
  const { data: configData } = useTerminalConfig();
  const [showLimitWarning, setShowLimitWarning] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);

  const terminalId = terminals?.[0]?.id ?? null;

  const openTerminal = async () => {
    const count = countData?.count ?? 0;
    const softLimit = configData?.soft_limit ?? 5;
    if (count >= softLimit) {
      setShowLimitWarning(true);
      return;
    }
    await doOpenTerminal();
  };

  const doOpenTerminal = async () => {
    setShowLimitWarning(false);
    try {
      await createTerminal.mutateAsync({ issue_id: issueId, project_id: projectId });
    } catch (err) {
      toast.error("Failed to open terminal: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  };

  const closeTerminal = async () => {
    setShowCloseConfirm(false);
    if (terminalId) {
      try {
        await killTerminal.mutateAsync(terminalId);
      } catch {
        // Terminal may already be dead
      }
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (!issue) {
    return (
      <div className="p-6">
        <p className="text-destructive">Issue not found.</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-1rem)] flex flex-col">
      {/* Terminal action bar */}
      <div className="flex items-center justify-end gap-2 px-6 py-2 border-b flex-shrink-0">
        {terminalId ? (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowCloseConfirm(true)}
          >
            <Square className="size-3 mr-1" />
            Close Terminal
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={openTerminal}
            disabled={createTerminal.isPending}
          >
            <Play className="size-3 mr-1" />
            {createTerminal.isPending ? "Opening..." : "Open Terminal"}
          </Button>
        )}
      </div>

      {/* Split view */}
      <ResizablePanelGroup direction="horizontal" className="flex-1 min-h-0">
        <ResizablePanel defaultSize={terminalId ? 60 : 100} minSize={30}>
          <ScrollArea className="h-full">
            <IssueDetail issue={issue} projectId={projectId} terminalId={terminalId} />
          </ScrollArea>
        </ResizablePanel>

        {terminalId && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={40} minSize={20}>
              <TerminalPanel
                terminalId={terminalId}
                onSessionEnd={() => {
                  killTerminal.mutate(terminalId);
                }}
              />
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>

      {/* Limit warning dialog */}
      <Dialog open={showLimitWarning} onOpenChange={setShowLimitWarning}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Terminal Limit Reached</DialogTitle>
            <DialogDescription>
              You have reached the soft limit of open terminals. Consider closing unused terminals to free resources.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLimitWarning(false)}>
              Cancel
            </Button>
            <Button onClick={doOpenTerminal}>Open Anyway</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Close confirmation dialog */}
      <Dialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Close Terminal?</DialogTitle>
            <DialogDescription>
              This will kill the terminal process. Any running commands will be terminated.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCloseConfirm(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={closeTerminal}>
              Close Terminal
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/projects/$projectId/issues/ frontend/src/features/issues/components/ frontend/src/features/terminals/components/terminal-panel.tsx
git commit -m "feat: add issue detail route with split-view terminal panel"
```

---

### Task 14: New Issue Route

**Files:**
- Create: `frontend/src/routes/projects/$projectId/issues/new.tsx`

- [ ] **Step 1: Write new issue route**

`frontend/src/routes/projects/$projectId/issues/new.tsx`:
```typescript
import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useCreateIssue } from "@/features/issues/hooks";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";

export const Route = createFileRoute("/projects/$projectId/issues/new")({
  component: NewIssuePage,
});

function NewIssuePage() {
  const { projectId } = Route.useParams();
  const navigate = useNavigate();
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState(3);
  const createIssue = useCreateIssue(projectId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createIssue.mutate(
      { description, priority },
      {
        onSuccess: () => {
          navigate({
            to: "/projects/$projectId/issues",
            params: { projectId },
          });
        },
      },
    );
  };

  return (
    <div className="p-6 max-w-lg">
      <h1 className="text-xl font-bold mb-6">New Issue</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium">Description</label>
          <Textarea
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            placeholder="Describe what needs to be done..."
          />
        </div>

        <div>
          <label className="text-sm font-medium">Priority</label>
          <Select
            value={String(priority)}
            onValueChange={(v) => setPriority(Number(v))}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">1 (Highest)</SelectItem>
              <SelectItem value="2">2</SelectItem>
              <SelectItem value="3">3</SelectItem>
              <SelectItem value="4">4</SelectItem>
              <SelectItem value="5">5 (Lowest)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {createIssue.error && (
          <p className="text-sm text-destructive">{createIssue.error.message}</p>
        )}

        <div className="flex gap-3">
          <Button type="submit" disabled={createIssue.isPending}>
            {createIssue.isPending ? "Creating..." : "Create"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              navigate({ to: "/projects/$projectId/issues", params: { projectId } })
            }
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/routes/projects/$projectId/issues/new.tsx
git commit -m "feat: add new issue route"
```

---

### Task 15: Files Route

**Files:**
- Create: `frontend/src/routes/projects/$projectId/files.tsx`
- Create: `frontend/src/features/files/components/file-gallery.tsx`

- [ ] **Step 1: Write file gallery component**

`frontend/src/features/files/components/file-gallery.tsx`:
```typescript
import { useRef } from "react";
import { Download, Trash2, Upload } from "lucide-react";
import { useFiles, useAllowedFormats, useUploadFiles, useDeleteFile } from "@/features/files/hooks";
import { getFileDownloadUrl } from "@/features/files/api";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

interface FileGalleryProps {
  projectId: string;
}

export function FileGallery({ projectId }: FileGalleryProps) {
  const { data: files, isLoading } = useFiles(projectId);
  const { data: formats } = useAllowedFormats();
  const uploadFiles = useUploadFiles(projectId);
  const deleteFile = useDeleteFile(projectId);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files;
    if (!selected || selected.length === 0) return;

    const formData = new FormData();
    for (const file of selected) {
      formData.append("files", file);
    }

    uploadFiles.mutate(formData, {
      onSettled: () => {
        if (inputRef.current) inputRef.current.value = "";
      },
    });
  };

  const handleDelete = (fileId: string, fileName: string) => {
    if (!window.confirm(`Delete "${fileName}"?`)) return;
    deleteFile.mutate(fileId);
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <Button asChild disabled={uploadFiles.isPending}>
          <label className="cursor-pointer">
            <Upload className="size-4 mr-2" />
            {uploadFiles.isPending ? "Uploading..." : "Upload Files"}
            <input
              ref={inputRef}
              type="file"
              multiple
              accept={formats?.accept || ""}
              onChange={handleUpload}
              disabled={uploadFiles.isPending}
              className="hidden"
            />
          </label>
        </Button>
        {formats?.label && (
          <span className="text-xs text-muted-foreground">{formats.label}</span>
        )}
      </div>

      {uploadFiles.error && (
        <p className="text-sm text-destructive mb-3">{uploadFiles.error.message}</p>
      )}

      {!files || files.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No files uploaded.</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Name</th>
              <th className="py-2 pr-4 font-medium">Type</th>
              <th className="py-2 pr-4 font-medium">Size</th>
              <th className="py-2 pr-4 font-medium">Uploaded</th>
              <th className="py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.id} className="border-b hover:bg-accent">
                <td className="py-2 pr-4 font-medium truncate max-w-xs" title={f.original_name}>
                  {f.original_name}
                </td>
                <td className="py-2 pr-4 text-muted-foreground uppercase">{f.file_type}</td>
                <td className="py-2 pr-4 text-muted-foreground">{formatSize(f.file_size)}</td>
                <td className="py-2 pr-4 text-muted-foreground">{formatDate(f.created_at)}</td>
                <td className="py-2 flex gap-2">
                  <Button variant="ghost" size="sm" asChild>
                    <a href={getFileDownloadUrl(projectId, f.id)} download>
                      <Download className="size-3 mr-1" />
                      Download
                    </a>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => handleDelete(f.id, f.original_name)}
                  >
                    <Trash2 className="size-3 mr-1" />
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write files route**

`frontend/src/routes/projects/$projectId/files.tsx`:
```typescript
import { createFileRoute } from "@tanstack/react-router";
import { FileGallery } from "@/features/files/components/file-gallery";

export const Route = createFileRoute("/projects/$projectId/files")({
  component: FilesPage,
});

function FilesPage() {
  const { projectId } = Route.useParams();

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-6">Files</h1>
      <FileGallery projectId={projectId} />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/projects/$projectId/files.tsx frontend/src/features/files/components/file-gallery.tsx
git commit -m "feat: add files route and file gallery component"
```

---

### Task 16: Terminal Commands Route

**Files:**
- Create: `frontend/src/routes/projects/$projectId/commands.tsx`
- Create: `frontend/src/features/terminals/components/terminal-commands-editor.tsx`

- [ ] **Step 1: Write terminal commands editor (shared between project and settings)**

`frontend/src/features/terminals/components/terminal-commands-editor.tsx`:
```typescript
import { useState } from "react";
import { ArrowDown, ArrowUp, Plus, X } from "lucide-react";
import {
  useTerminalCommands,
  useTerminalCommandVariables,
  useCreateTerminalCommand,
  useUpdateTerminalCommand,
  useReorderTerminalCommands,
  useDeleteTerminalCommand,
} from "@/features/terminals/hooks";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";

interface TerminalCommandsEditorProps {
  projectId?: string | null;
}

export function TerminalCommandsEditor({ projectId = null }: TerminalCommandsEditorProps) {
  const { data: commands, isLoading } = useTerminalCommands(projectId);
  const { data: variables } = useTerminalCommandVariables();
  const createCommand = useCreateTerminalCommand(projectId);
  const updateCommand = useUpdateTerminalCommand(projectId);
  const reorderCommands = useReorderTerminalCommands(projectId);
  const deleteCommand = useDeleteTerminalCommand(projectId);
  const [newCmd, setNewCmd] = useState("");

  const handleAdd = () => {
    const trimmed = newCmd.trim();
    if (!trimmed) return;
    const sortOrder = commands && commands.length > 0
      ? Math.max(...commands.map((c) => c.sort_order)) + 1
      : 0;
    createCommand.mutate(
      { command: trimmed, sort_order: sortOrder, project_id: projectId },
      { onSuccess: () => setNewCmd("") },
    );
  };

  const handleBlur = (cmd: { id: number; command: string }, newValue: string) => {
    const trimmed = newValue.trim();
    if (!trimmed || trimmed === cmd.command) return;
    updateCommand.mutate({ id: cmd.id, data: { command: trimmed } });
  };

  const handleMove = (index: number, direction: number) => {
    if (!commands) return;
    const swapIndex = index + direction;
    if (swapIndex < 0 || swapIndex >= commands.length) return;
    reorderCommands.mutate([
      { id: commands[index].id, sort_order: commands[swapIndex].sort_order },
      { id: commands[swapIndex].id, sort_order: commands[index].sort_order },
    ]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-10" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {commands?.length === 0 && projectId != null && (
        <p className="text-sm text-muted-foreground italic">
          No project commands configured. Global commands will be used.
        </p>
      )}

      {commands?.map((cmd, index) => (
        <div key={cmd.id} className="flex items-center gap-2">
          <div className="flex flex-col gap-0.5">
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={() => handleMove(index, -1)}
              disabled={index === 0}
            >
              <ArrowUp className="size-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={() => handleMove(index, 1)}
              disabled={index === (commands?.length ?? 0) - 1}
            >
              <ArrowDown className="size-3" />
            </Button>
          </div>
          <Input
            defaultValue={cmd.command}
            onBlur={(e) => handleBlur(cmd, e.target.value)}
            className="flex-1 font-mono text-sm"
          />
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-destructive"
            onClick={() => deleteCommand.mutate(cmd.id)}
          >
            <X className="size-4" />
          </Button>
        </div>
      ))}

      <div className="flex gap-2 mt-3">
        <Input
          value={newCmd}
          onChange={(e) => setNewCmd(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a command..."
          className="flex-1 font-mono text-sm"
        />
        <Button
          onClick={handleAdd}
          disabled={!newCmd.trim()}
          size="sm"
        >
          <Plus className="size-4 mr-1" />
          Add
        </Button>
      </div>

      {variables && variables.length > 0 && (
        <div className="mt-4 p-3 bg-muted rounded-md text-sm">
          <p className="font-medium mb-1">Available variables</p>
          <div className="space-y-0.5">
            {variables.map((v) => (
              <p key={v.name} className="text-muted-foreground">
                <code className="text-primary bg-primary/10 px-1 rounded font-mono">
                  {v.name}
                </code>{" "}
                — {v.description}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write commands route**

`frontend/src/routes/projects/$projectId/commands.tsx`:
```typescript
import { createFileRoute } from "@tanstack/react-router";
import { TerminalCommandsEditor } from "@/features/terminals/components/terminal-commands-editor";

export const Route = createFileRoute("/projects/$projectId/commands")({
  component: CommandsPage,
});

function CommandsPage() {
  const { projectId } = Route.useParams();

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-2">Terminal Commands</h1>
      <p className="text-sm text-muted-foreground mb-6">
        These commands run when opening a terminal for this project. When set, they override the global terminal commands.
      </p>
      <TerminalCommandsEditor projectId={projectId} />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/projects/$projectId/commands.tsx frontend/src/features/terminals/components/terminal-commands-editor.tsx
git commit -m "feat: add terminal commands route and editor component"
```

---

### Task 17: Terminals Page (Global)

**Files:**
- Create: `frontend/src/routes/terminals.tsx`

- [ ] **Step 1: Write terminals route**

`frontend/src/routes/terminals.tsx`:
```typescript
import { createFileRoute, Link } from "@tanstack/react-router";
import { ExternalLink, Skull } from "lucide-react";
import { useTerminals, useTerminalConfig, useKillTerminal } from "@/features/terminals/hooks";
import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

function formatAge(createdAt: string): string {
  const diff = Date.now() - new Date(createdAt).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  return `${hours}h ${mins % 60}m ago`;
}

export const Route = createFileRoute("/terminals")({
  component: TerminalsPage,
});

function TerminalsPage() {
  const { data: terminals, isLoading } = useTerminals();
  const { data: config } = useTerminalConfig();
  const killTerminal = useKillTerminal();
  const softLimit = config?.soft_limit ?? 5;

  const handleKill = (terminalId: string) => {
    if (!confirm("Kill this terminal? Any running commands will be terminated.")) return;
    killTerminal.mutate(terminalId);
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-48" />
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-semibold">Active Terminals</h1>
        <span className="text-sm text-muted-foreground">
          {terminals?.length ?? 0} / {softLimit} (soft limit)
        </span>
      </div>

      {!terminals || terminals.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No active terminals.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {terminals.map((term) => (
            <div
              key={term.id}
              className="flex items-center rounded-md border px-4 py-3"
            >
              <span
                className="w-2.5 h-2.5 rounded-full bg-green-400 mr-4 flex-shrink-0"
                style={{ boxShadow: "0 0 6px #4ade80" }}
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium">{term.issue_name || term.issue_id}</p>
                <p className="text-sm text-muted-foreground">
                  <span className="text-primary">{term.project_name || term.project_id}</span>
                  {" · "}Started {formatAge(term.created_at)}
                </p>
              </div>
              <div className="flex gap-2 ml-4">
                <Button variant="outline" size="sm" asChild>
                  <Link
                    to="/projects/$projectId/issues/$issueId"
                    params={{ projectId: term.project_id, issueId: term.issue_id }}
                  >
                    <ExternalLink className="size-3 mr-1" />
                    Go to Issue
                  </Link>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={() => handleKill(term.id)}
                >
                  <Skull className="size-3 mr-1" />
                  Kill
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/routes/terminals.tsx
git commit -m "feat: add global terminals page"
```

---

### Task 18: Settings Page

**Files:**
- Create: `frontend/src/routes/settings.tsx`
- Create: `frontend/src/features/settings/components/settings-form.tsx`

- [ ] **Step 1: Write settings form component (deduplicated setting field)**

`frontend/src/features/settings/components/settings-form.tsx`:
```typescript
import { useState } from "react";
import { RotateCcw } from "lucide-react";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/shared/components/ui/tooltip";
import { useUpdateSetting, useResetSetting } from "@/features/settings/hooks";
import type { Setting } from "@/shared/types";

function formatLabel(key: string): string {
  const parts = key.split(".");
  if (parts[0] === "tool" || parts[0] === "server") {
    return parts[1].replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return key;
}

interface SettingFieldProps {
  setting: Setting;
}

function SettingField({ setting }: SettingFieldProps) {
  const [value, setValue] = useState(setting.value);
  const updateSetting = useUpdateSetting();
  const resetSetting = useResetSetting();

  const isDirty = value !== setting.value;

  const handleSave = () => {
    updateSetting.mutate({ key: setting.key, value });
  };

  const handleReset = () => {
    resetSetting.mutate(setting.key, {
      onSuccess: () => setValue(setting.default),
    });
  };

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <label className="font-medium text-sm">{formatLabel(setting.key)}</label>
        <div className="flex items-center gap-2">
          {setting.is_customized && (
            <Badge variant="secondary" className="text-xs">Customized</Badge>
          )}
          {setting.is_customized && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={handleReset}
                    disabled={resetSetting.isPending}
                  >
                    <RotateCcw className="size-3" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Reset to default</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </div>
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        rows={setting.key.endsWith(".description") ? 4 : 5}
        className="font-mono text-sm"
      />
      {!setting.is_customized && (
        <p className="text-xs text-muted-foreground mt-1">Default value</p>
      )}
      <div className="flex justify-end mt-2">
        <Button
          size="sm"
          onClick={handleSave}
          disabled={updateSetting.isPending || !isDirty}
        >
          {updateSetting.isPending ? "Saving..." : "Save"}
        </Button>
      </div>
    </div>
  );
}

interface SettingsFormProps {
  settings: Setting[];
}

export function SettingsForm({ settings }: SettingsFormProps) {
  if (settings.length === 0) {
    return <p className="text-sm text-muted-foreground">No settings in this category.</p>;
  }

  return (
    <div className="space-y-4">
      {settings.map((setting) => (
        <SettingField key={setting.key} setting={setting} />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Write settings route**

`frontend/src/routes/settings.tsx`:
```typescript
import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle } from "lucide-react";
import { useSettings, useResetAllSettings } from "@/features/settings/hooks";
import { SettingsForm } from "@/features/settings/components/settings-form";
import { TerminalCommandsEditor } from "@/features/terminals/components/terminal-commands-editor";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Skeleton } from "@/shared/components/ui/skeleton";
import type { Setting } from "@/shared/types";

const TABS = ["Server", "Tool Descriptions", "Response Messages", "Terminal"] as const;
type SettingsTab = (typeof TABS)[number];

function getCategory(key: string): string {
  if (key.startsWith("server.")) return "Server";
  if (key.endsWith(".description")) return "Tool Descriptions";
  if (key.endsWith(".response_message")) return "Response Messages";
  return "Other";
}

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const { data: settings, isLoading, error } = useSettings();
  const resetAll = useResetAllSettings();
  const [activeTab, setActiveTab] = useState<SettingsTab>("Server");
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-96" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-40" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-destructive">{error.message}</p>
      </div>
    );
  }

  const filteredSettings = (settings ?? []).filter(
    (s: Setting) => getCategory(s.key) === activeTab,
  );

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-6">Settings</h1>

      {/* Tabs */}
      <div className="flex gap-1.5 mb-6">
        {TABS.map((tab) => (
          <Button
            key={tab}
            variant={activeTab === tab ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab(tab)}
            className="text-xs"
          >
            {tab}
          </Button>
        ))}
      </div>

      {/* Warning banners */}
      {activeTab === "Server" && (
        <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 flex items-start gap-2">
          <AlertTriangle className="size-4 mt-0.5 flex-shrink-0" />
          Server name changes take effect after restarting the backend.
        </div>
      )}
      {activeTab === "Tool Descriptions" && (
        <div className="mb-5 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 flex items-start gap-2">
          <AlertTriangle className="size-4 mt-0.5 flex-shrink-0" />
          Tool description changes take effect after restarting the backend.
        </div>
      )}

      {/* Settings or Terminal Commands */}
      {activeTab === "Terminal" ? (
        <div>
          <div className="mb-5 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800">
            These commands run automatically when opening a terminal. They apply only when a project has no project-specific commands.
          </div>
          <TerminalCommandsEditor projectId={null} />
        </div>
      ) : (
        <SettingsForm settings={filteredSettings} />
      )}

      {/* Reset all */}
      {activeTab !== "Terminal" && (
        <div className="mt-8 pt-6 border-t">
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={() => setShowResetConfirm(true)}
          >
            Reset all to defaults
          </Button>
        </div>
      )}

      {/* Reset all confirmation */}
      <Dialog open={showResetConfirm} onOpenChange={setShowResetConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset All Settings?</DialogTitle>
            <DialogDescription>
              This will reset all settings to their default values. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowResetConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => resetAll.mutate(undefined, { onSuccess: () => setShowResetConfirm(false) })}
              disabled={resetAll.isPending}
            >
              {resetAll.isPending ? "Resetting..." : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/settings.tsx frontend/src/features/settings/components/settings-form.tsx
git commit -m "feat: add settings page with deduplicated setting fields"
```

---

### Task 19: New Project — Add Dialog to Index Page

**Files:**
- Modify: `frontend/src/routes/index.tsx`

- [ ] **Step 1: Update index route to include a "New Project" dialog**

Add a dialog to the index route (`frontend/src/routes/index.tsx`). Add a state `showNewProject`, a `Dialog` with the project creation form (same fields as the current `NewProjectPage`: name, path, description, tech_stack). Use `useCreateProject` mutation. On success, navigate to the new project's issues page.

Replace the `<Link to="/">` buttons with `<Button onClick={() => setShowNewProject(true)}>`.

The `NewProjectPage.jsx` route does not need a separate route anymore — it's a dialog accessible from the index page and from the project switcher's "New Project" item. Update the project switcher to also open a dialog or navigate to `/` where the dialog can be shown.

For simplicity, keep it as a separate route for now — create `frontend/src/routes/projects/new.tsx`:

```typescript
import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useCreateProject } from "@/features/projects/hooks";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";

export const Route = createFileRoute("/projects/new")({
  component: NewProjectPage,
});

function NewProjectPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    path: "",
    description: "",
    tech_stack: "",
  });
  const createProject = useCreateProject();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createProject.mutate(form, {
      onSuccess: (project) => {
        navigate({
          to: "/projects/$projectId/issues",
          params: { projectId: project.id },
        });
      },
    });
  };

  return (
    <div className="p-6 max-w-lg">
      <h1 className="text-xl font-bold mb-6">New Project</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium">Name</label>
          <Input
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </div>
        <div>
          <label className="text-sm font-medium">Path</label>
          <Input
            required
            value={form.path}
            onChange={(e) => setForm({ ...form, path: e.target.value })}
            className="font-mono"
            placeholder="/home/user/my-project"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Description</label>
          <Textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={4}
            placeholder="Describe the project context..."
          />
        </div>
        <div>
          <label className="text-sm font-medium">Tech Stack</label>
          <Textarea
            value={form.tech_stack}
            onChange={(e) => setForm({ ...form, tech_stack: e.target.value })}
            rows={3}
            placeholder="Languages, frameworks, databases..."
          />
        </div>

        {createProject.error && (
          <p className="text-sm text-destructive">{createProject.error.message}</p>
        )}

        <div className="flex gap-3">
          <Button type="submit" disabled={createProject.isPending}>
            {createProject.isPending ? "Creating..." : "Create"}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate({ to: "/" })}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
```

Also update `frontend/src/routes/index.tsx`: change the "New Project" button link to navigate to `/projects/new`:

```typescript
// Change this in the index route:
<Link to="/projects/new">
```

And update `frontend/src/features/projects/components/project-switcher.tsx`: change the "New Project" menu item to navigate to `/projects/new` instead of `/`.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/routes/projects/new.tsx frontend/src/routes/index.tsx frontend/src/features/projects/components/project-switcher.tsx
git commit -m "feat: add new project route"
```

---

### Task 20: MCP Setup Dialog

**Files:**
- Create: `frontend/src/features/projects/components/mcp-setup-dialog.tsx`

- [ ] **Step 1: Write MCP setup dialog**

`frontend/src/features/projects/components/mcp-setup-dialog.tsx`:
```typescript
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Separator } from "@/shared/components/ui/separator";

interface McpSetupDialogProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function McpSetupDialog({ projectId, open, onOpenChange }: McpSetupDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>MCP Server Setup</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-sm mb-1">Endpoint URL</h3>
            <code className="block bg-muted rounded px-3 py-2 text-sm font-mono break-all">
              http://localhost:8000/mcp/
            </code>
          </div>

          <Separator />

          <div>
            <h3 className="font-medium text-sm mb-2">Claude Code</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Run this command in your terminal:
            </p>
            <pre className="bg-muted rounded px-3 py-2 text-sm font-mono overflow-x-auto">
              claude mcp add --transport http ManagerAi http://localhost:8000/mcp/
            </pre>
          </div>

          <Separator />

          <div>
            <h3 className="font-medium text-sm mb-2">Other MCP Clients</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Add this to your client configuration (Streamable HTTP):
            </p>
            <pre className="bg-muted rounded px-3 py-2 text-sm font-mono overflow-x-auto whitespace-pre">
              {JSON.stringify(
                {
                  mcpServers: {
                    ManagerAi: {
                      type: "url",
                      url: "http://localhost:8000/mcp/",
                    },
                  },
                },
                null,
                2,
              )}
            </pre>
          </div>

          <Separator />

          <div>
            <h3 className="font-medium text-sm mb-1">Project ID</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Most tools require the <code className="bg-muted px-1 rounded">project_id</code> parameter:
            </p>
            <code className="block bg-muted rounded px-3 py-2 text-sm font-mono break-all">
              {projectId}
            </code>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
            <p className="text-sm text-blue-800">
              <span className="font-medium">Tip:</span> Use the "Install manager.json" action to automatically place the project ID file in your project root.
            </p>
          </div>
        </div>

        <Button variant="outline" className="w-full" onClick={() => onOpenChange(false)}>
          Close
        </Button>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/projects/components/mcp-setup-dialog.tsx
git commit -m "feat: add MCP setup dialog component"
```

---

### Task 21: Project Summary — Add to Sidebar via Dropdown Actions

**Files:**
- Modify: `frontend/src/shared/components/app-sidebar.tsx`

- [ ] **Step 1: Add project actions to the sidebar**

Add a section to the sidebar under the project navigation links that includes:
- "Edit Project" → opens `ProjectSettingsDialog`
- "Install manager.json" → calls `useInstallManagerJson`
- "Install Claude Resources" → calls `useInstallClaudeResources`
- "Export manager.json" → triggers file download
- "MCP Setup" → opens `McpSetupDialog`

These replace the Summary tab from the old `ProjectDetailPage`. Add them as a `DropdownMenu` on the project name in the sidebar header, or as a `SidebarGroup` with action buttons.

Implementation: Add a "Project Actions" entry to the project nav in `app-sidebar.tsx` that opens a dropdown menu with all these actions. Import and render the `ProjectSettingsDialog` and `McpSetupDialog` as needed, with their `open` state managed locally.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/shared/components/app-sidebar.tsx
git commit -m "feat: add project actions to sidebar (edit, install, MCP setup)"
```

---

### Task 22: Cleanup — Remove Old JS Files

**Files:**
- Delete: `frontend/src/api/client.js`
- Delete: `frontend/src/context/EventContext.jsx`
- Delete: `frontend/src/pages/ProjectsPage.jsx`
- Delete: `frontend/src/pages/NewProjectPage.jsx`
- Delete: `frontend/src/pages/ProjectDetailPage.jsx`
- Delete: `frontend/src/pages/NewIssuePage.jsx`
- Delete: `frontend/src/pages/IssueDetailPage.jsx`
- Delete: `frontend/src/pages/TerminalsPage.jsx`
- Delete: `frontend/src/pages/SettingsPage.jsx`
- Delete: `frontend/src/components/ProjectCard.jsx`
- Delete: `frontend/src/components/IssueList.jsx`
- Delete: `frontend/src/components/StatusBadge.jsx`
- Delete: `frontend/src/components/ToastContainer.jsx`
- Delete: `frontend/src/components/MarkdownViewer.jsx`
- Delete: `frontend/src/components/FileGallery.jsx`
- Delete: `frontend/src/components/TerminalPanel.jsx`
- Delete: `frontend/src/components/TerminalCommandsEditor.jsx`

- [ ] **Step 1: Delete all old JS source files**

```bash
cd frontend/src
rm -rf api/ context/ pages/ components/
```

Note: `components/` directory now only exists under `shared/components/` and `features/*/components/`. The old top-level `components/` directory should be removed entirely.

- [ ] **Step 2: Remove react-router-dom from eslint config if referenced**

Check `frontend/eslint.config.js` and update if needed for TypeScript.

- [ ] **Step 3: Regenerate route tree and verify build**

```bash
cd frontend
npx tsr generate
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add -A frontend/
git commit -m "chore: remove old JavaScript source files and complete TS migration"
```

---

### Task 23: Final Verification

- [ ] **Step 1: Start the full stack and verify all functionality**

```bash
cd C:/Users/jacob/Desktop/manager_ai
python start.py
```

Verify in the browser:
1. Home page shows projects list
2. Sidebar shows project switcher, navigation updates on project change
3. Issues list renders with status filters
4. Issue detail shows split view with terminal on right
5. Terminal opens, connects via WebSocket, is resizable
6. Files page allows upload/download/delete
7. Terminal commands editor works in both project and global contexts
8. Settings page shows all categories, save/reset works
9. Terminals page shows active terminals with kill/navigate actions
10. Toast notifications appear on WebSocket events
11. New project and new issue creation works
12. MCP setup dialog shows correct info

- [ ] **Step 2: Final commit if any fixes needed**

```bash
git add -A frontend/
git commit -m "fix: address issues found during final verification"
```
