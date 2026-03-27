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
