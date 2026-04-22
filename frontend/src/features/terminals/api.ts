import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";
import type { AskTerminalCreate, Terminal, TerminalCommand, TerminalCommandCreate, TerminalCommandTemplate, TerminalCommandUpdate, TerminalCommandVariable, TerminalCreate, TerminalListItem } from "@/shared/types";

export function fetchTerminals(projectId?: string, issueId?: string): Promise<TerminalListItem[]> {
  const params = new URLSearchParams();
  if (projectId) params.set("project_id", projectId);
  if (issueId) params.set("issue_id", issueId);
  const qs = params.toString();
  return apiGet<TerminalListItem[]>(`/terminals${qs ? `?${qs}` : ""}`);
}

export function createTerminal(data: TerminalCreate): Promise<Terminal> {
  return apiPost<Terminal>("/terminals", data);
}

export function createAskTerminal(data: AskTerminalCreate): Promise<Terminal> {
  return apiPost<Terminal>("/terminals/ask", data);
}

export function fetchAskTerminals(projectId: string): Promise<TerminalListItem[]> {
  return apiGet<TerminalListItem[]>(`/terminals/ask?project_id=${encodeURIComponent(projectId)}`);
}

export function killTerminal(terminalId: string): Promise<null> {
  return apiDelete(`/terminals/${terminalId}`);
}

export function fetchTerminalCount(): Promise<{ count: number }> {
  return apiGet<{ count: number }>("/terminals/count");
}

export function fetchTerminalConfig(): Promise<{ soft_limit: number }> {
  return apiGet<{ soft_limit: number }>("/terminals/config");
}

export function fetchTerminalCommandVariables(): Promise<TerminalCommandVariable[]> {
  return apiGet<TerminalCommandVariable[]>("/terminal-commands/variables");
}

export function fetchTerminalCommands(projectId?: string | null): Promise<TerminalCommand[]> {
  const params = projectId != null ? `?project_id=${projectId}` : "";
  return apiGet<TerminalCommand[]>(`/terminal-commands${params}`);
}

export function createTerminalCommand(data: TerminalCommandCreate): Promise<TerminalCommand> {
  return apiPost<TerminalCommand>("/terminal-commands", data);
}

export function updateTerminalCommand(id: number, data: TerminalCommandUpdate): Promise<TerminalCommand> {
  return apiPut<TerminalCommand>(`/terminal-commands/${id}`, data);
}

export function reorderTerminalCommands(commands: { id: number; sort_order: number }[]): Promise<TerminalCommand[]> {
  return apiPut<TerminalCommand[]>("/terminal-commands/reorder", { commands });
}

export function deleteTerminalCommand(id: number): Promise<null> {
  return apiDelete(`/terminal-commands/${id}`);
}

export function fetchTerminalCommandTemplates(): Promise<TerminalCommandTemplate[]> {
  return apiGet<TerminalCommandTemplate[]>("/terminal-commands/templates");
}
