import { apiGet, apiPut } from "@/shared/api/client";

export interface ProviderInfo {
  name: string;
  cli: string;
  flags: string[];
  description: string;
  example_run_issue: string;
  example_run_pipeline: string;
  is_builtin: boolean;
}

export function fetchAgentProviders(): Promise<string[]> {
  return apiGet<string[]>("/system/agent-providers");
}

export function fetchProviderDetails(): Promise<ProviderInfo[]> {
  return Promise.resolve([
    {
      name: "claude",
      cli: "claude",
      flags: ["--dangerously-skip-permissions"],
      description:
        "Anthropic Claude Code CLI — AI coding agent with built-in /run-issue, /run-pipeline, /ask-and-brainstorm commands.",
      example_run_issue: `claude --dangerously-skip-permissions "/run-issue iss-123"`,
      example_run_pipeline: `claude --dangerously-skip-permissions "/run-pipeline iss-123"`,
      is_builtin: true,
    },
    {
      name: "hermes",
      cli: "hermes",
      flags: ["--yolo", "--worktree"],
      description:
        "Nous Research Hermes Agent — CLI AI agent with skill-based workflow. Requires hermes-agent skills installed.",
      example_run_issue: `hermes chat --skills run-issue --worktree --yolo -q "Work on issue iss-123"`,
      example_run_pipeline: `hermes chat --skills run-pipeline --worktree --yolo -q "Execute pipeline step for issue iss-123"`,
      is_builtin: true,
    },
  ]);
}

interface SettingResponse {
  key: string;
  value: string;
  default: string;
  is_customized: boolean;
}

export function fetchAgentProviderSetting(): Promise<string> {
  return apiGet<SettingResponse>("/settings/agent_provider")
    .then((r) => r.value)
    .catch(() => "claude");
}

export function updateAgentProviderSetting(provider: string): Promise<void> {
  return apiPut("/settings/agent_provider", { value: provider });
}
