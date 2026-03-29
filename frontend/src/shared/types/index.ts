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
  name?: string;
  description?: string;
  priority?: number;
}

export interface IssueStatusUpdate {
  status: IssueStatus;
}

export interface IssueCompleteBody {
  recap: string;
}

export interface IssueFeedback {
  id: string;
  issue_id: string;
  content: string;
  created_at: string;
}

export interface IssueFeedbackCreate {
  content: string;
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
  shell?: string | null;
  created_at: string;
  updated_at: string;
  issue_counts?: Record<string, number>;
}

export interface ProjectCreate {
  name: string;
  path: string;
  description?: string;
  tech_stack?: string;
  shell?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  path?: string;
  description?: string | null;
  tech_stack?: string | null;
  shell?: string | null;
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
  run_commands?: boolean;
}

export interface AskTerminalCreate {
  project_id: string;
}

// ── Terminal Command ──

export interface TerminalCommand {
  id: number;
  command: string;
  sort_order: number;
  project_id: string | null;
  condition?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TerminalCommandCreate {
  command: string;
  sort_order: number;
  project_id?: string | null;
  condition?: string | null;
}

export interface TerminalCommandUpdate {
  command?: string;
  sort_order?: number;
  condition?: string | null;
}

export interface TerminalCommandVariable {
  name: string;
  description: string;
}

export interface TerminalCommandTemplate {
  name: string;
  command: string;
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

// ── Activity ──

export interface ActivityLog {
  id: string;
  project_id: string;
  issue_id: string | null;
  event_type: string;
  details: Record<string, unknown>;
  created_at: string;
}

// ── Library ──

export interface SkillMeta {
  name: string;
  category: string;
  description: string;
  built_in: boolean;
  type: "skill" | "agent";
}

export interface SkillDetail extends SkillMeta {
  content: string;
}

export interface SkillCreate {
  name: string;
  category: string;
  description: string;
  content: string;
  type: string;
}

export interface ProjectSkill {
  id: number;
  project_id: string;
  name: string;
  type: "skill" | "agent";
  assigned_at: string;
  file_synced: boolean;
}

export interface ProjectSkillAssign {
  name: string;
  type: "skill" | "agent";
}

// ── Project Variable ──

export interface ProjectVariable {
  id: number;
  project_id: string;
  name: string;
  value: string;
  is_secret: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectVariableCreate {
  name: string;
  value: string;
  is_secret?: boolean;
}

export interface ProjectVariableUpdate {
  name?: string;
  value?: string;
  is_secret?: boolean;
}

// ── Prompt Templates ──

export interface TemplateInfo {
  type: string;
  content: string;
  is_overridden: boolean;
}

export interface TemplateSave {
  content: string;
}

// ── Dashboard ──

export interface DashboardIssue {
  id: string;
  name: string | null;
  description: string;
  status: IssueStatus;
  priority: number;
}

export interface DashboardProject {
  id: string;
  name: string;
  path: string;
  active_issues: DashboardIssue[];
}

// ── Issue Relations ──

export type RelationType = "blocks" | "related";

export interface IssueRelation {
  id: number;
  source_id: string;
  target_id: string;
  relation_type: RelationType;
  created_at: string;
}

export interface IssueRelationCreate {
  target_id: string;
  relation_type: RelationType;
}
