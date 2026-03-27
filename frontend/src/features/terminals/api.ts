import { request } from "@/shared/api/client";
import type { Terminal, TerminalCommand, TerminalCommandCreate, TerminalCommandUpdate, TerminalCommandVariable, TerminalCreate, TerminalListItem } from "@/shared/types";

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
