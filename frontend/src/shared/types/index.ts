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
  wsl_distro?: string | null;
  created_at: string;
  updated_at: string;
  archived_at?: string | null;
  issue_counts?: Record<string, number>;
}

export interface ProjectCreate {
  name: string;
  path: string;
  description?: string;
  tech_stack?: string;
  shell?: string | null;
  wsl_distro?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  path?: string;
  description?: string | null;
  tech_stack?: string | null;
  shell?: string | null;
  wsl_distro?: string | null;
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

// ── System ──

export interface SystemInfo {
  platform: string;
  wsl_available: boolean;
  distros: string[];
  default_distro: string | null;
  host_ip_for_wsl: string | null;
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

export const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp"] as const;
export type ImageExtension = (typeof IMAGE_EXTENSIONS)[number];

export function isImageExtension(ext: string): ext is ImageExtension {
  return (IMAGE_EXTENSIONS as readonly string[]).includes(ext.toLowerCase());
}

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
  extraction_status?: string | null;
}

export interface AllowedFormats {
  accept: string;
  extensions: string[];
  label: string;
}

// ── Memory ──

export interface Memory {
  id: string;
  project_id: string;
  title: string;
  description: string;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
  children_count: number;
  links_out_count: number;
  links_in_count: number;
}

export interface MemoryLink {
  from_id: string;
  to_id: string;
  relation: string;
  created_at: string;
}

export interface MemoryDetail extends Memory {
  parent: Memory | null;
  children: Memory[];
  links_out: MemoryLink[];
  links_in: MemoryLink[];
}

export interface MemorySearchHit {
  memory: Memory;
  snippet: string;
  rank: number;
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
  /** Empty string on list responses when `is_secret` is true. Fetch the
   * real value via the `/reveal` endpoint. */
  value: string;
  has_value: boolean;
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
