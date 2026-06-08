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
  category: string | null;
  plan: string | null;
  specification: string | null;
  recap: string | null;
  tags: string[];
  tasks: Task[];
  created_at: string;
  updated_at: string;
  finished_at: string | null;
}

export interface IssueCreate {
  description: string;
  priority?: number;
  category?: string | null;
  tags?: string[];
  source_issue_id?: string;
}

export interface IssueUpdate {
  name?: string;
  description?: string;
  priority?: number;
  category?: string | null;
  tags?: string[];
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
  url?: string | null;
  created_at: string;
  updated_at: string;
  archived_at?: string | null;
  favorited_at?: string | null;
  issue_counts?: Record<string, number>;
}

export interface ProjectCreate {
  name: string;
  path: string;
  description?: string;
  tech_stack?: string;
  shell?: string | null;
  wsl_distro?: string | null;
  url?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  path?: string;
  description?: string | null;
  tech_stack?: string | null;
  shell?: string | null;
  wsl_distro?: string | null;
  url?: string | null;
  favorited_at?: string | null;
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
  command?: string;
}

export interface AskTerminalCreate {
  project_id: string;
}

export interface LogTerminalCreate {
  project_id: string;
  issue_id: string;
  label?: string;
}

export interface ManageAgentTerminalCreate { agent_id?: string }

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

// ── Project Links ──

export interface ProjectLink {
  id: string;
  source_project_id: string;
  source_project_name: string;
  target_project_id: string;
  target_project_name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectLinkCreate {
  target_project_id: string;
  description: string;
}

export interface ProjectLinkUpdate {
  description: string;
}

// ── Export / Import ──

export interface ProjectLink {

export interface AgentExportItem {
  id: string;
  name: string;
  provider: string | null;
  model: string | null;
  allowed_tools: string[] | null;
  intent: string;
}

export interface PipelineStepExportItem {
  id: string;
  pipeline_id: string;
  agent_id: string;
  order_index: number;
  agent: AgentExportItem;
}

export interface PipelineExportItem {
  id: string;
  name: string;
  steps: PipelineStepExportItem[];
}

export interface ExportWrapper<T> {
  version: number;
  type: string;
  exported_at: string;
  items: T[];
}

export interface ImportConflict<T> {
  incoming: T;
  existing: T;
}

export interface ImportPreviewResponse<T> {
  conflicts: ImportConflict<T>[];
  new: T[];
  total: number;
}

export interface PipelineImportPreviewResponse<T> {
  conflicts: ImportConflict<T>[];
  new: T[];
  missing_agents: { agent_id: string; name: string }[];
  total: number;
}

export interface ImportConfirmResponse {
  imported: number;
  skipped: number;
  errors: string[];
}

// ── Question ──

export interface Question {
  id: string;
  project_id: string;
  issue_id: string;
  project_name?: string;
  issue_name?: string;
  question: string;
  options: string[] | null;
  status: "pending" | "answered" | "timed_out";
  answer: string | null;
  selected_option: string | null;
  created_at: string | null;
  answered_at: string | null;
}

export interface QuestionAnswer {
  answer: string;
  selected_option: string | null;
}

// ── Agent ──

export interface Agent {
  id: string;
  name: string;
  provider: string | null;
  model: string | null;
  allowed_tools: string[] | null;
  intent: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentCreate {
  name: string;
  provider?: string | null;
  model?: string | null;
  allowed_tools?: string[] | null;
  intent?: string;
}

export interface AgentUpdate {
  name?: string;
  provider?: string | null;
  model?: string | null;
  allowed_tools?: string[] | null;
  intent?: string | null;
}

// ── Pipeline ──

export interface PipelineStep {
  id: string;
  pipeline_id: string;
  agent_id: string;
  order_index: number;
}

export interface PipelineStepCreate {
  agent_id: string;
  order_index?: number;
}

export interface Pipeline {
  id: string;
  name: string;
  steps: PipelineStep[];
  created_at: string | null;
  updated_at: string | null;
}

export interface PipelineCreate {
  name: string;
  steps?: PipelineStepCreate[];
}

export interface PipelineUpdate {
  name: string;
}

export interface StepReorderRequest {
  step_ids: string[];
}

// ── Pipeline Event Rules ──

export interface PipelineEventRule {
  id: string;
  pipeline_id: string;
  event_type: string;
  source_step_id: string;
  target_step_id: string;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface PipelineEventRuleCreate {
  event_type: string;
  source_step_id: string;
  target_step_id: string;
}

// ── Pipeline Run ──

export type PipelineRunStatus = "RUNNING" | "COMPLETED" | "FAILED";

export type PipelineStepRunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface PipelineStepRun {
  id: string;
  pipeline_run_id: string;
  pipeline_step_id: string;
  agent_name: string;
  status: PipelineStepRunStatus;
  terminal_id: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface PipelineRun {
  id: string;
  pipeline_id: string;
  pipeline_name: string;
  issue_id: string;
  status: PipelineRunStatus;
  current_step_index: number;
  steps: PipelineStepRun[];
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export interface PipelineRunStart {
  pipeline_id: string;
  issue_id: string;
  project_id: string;
}

// ── Pipeline Message ──

export interface PipelineMessage {
  id: string;
  pipeline_run_id: string;
  sender_agent_name: string;
  content: string;
  created_at: string | null;
}

export interface PipelineMessageCreate {
  sender_agent_name: string;
  content: string;
}
