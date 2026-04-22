import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { AskTerminalCreate, TerminalCreate, TerminalCommandUpdate } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const terminalKeys = {
  all: ["terminals"] as const,
  count: ["terminals", "count"] as const,
  config: ["terminals", "config"] as const,
  ask: (projectId: string) => ["terminals", "ask", projectId] as const,
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
    onError: onMutationError,
  });
}

export function useCreateAskTerminal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AskTerminalCreate) => api.createAskTerminal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.all });
      queryClient.invalidateQueries({ queryKey: terminalKeys.count });
    },
    onError: onMutationError,
  });
}

export function useAskTerminals(projectId: string) {
  return useQuery({
    queryKey: terminalKeys.ask(projectId),
    queryFn: () => api.fetchAskTerminals(projectId),
    enabled: Boolean(projectId),
    staleTime: 10_000,
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
    onError: onMutationError,
  });
}

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
    onError: onMutationError,
  });
}

export function useUpdateTerminalCommand(projectId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TerminalCommandUpdate }) =>
      api.updateTerminalCommand(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.commands(projectId) });
    },
    onError: onMutationError,
  });
}

export function useReorderTerminalCommands(projectId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (commands: { id: number; sort_order: number }[]) => api.reorderTerminalCommands(commands),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.commands(projectId) });
    },
    onError: onMutationError,
  });
}

export function useDeleteTerminalCommand(projectId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteTerminalCommand(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.commands(projectId) });
    },
    onError: onMutationError,
  });
}

export function useTerminalCommandTemplates() {
  return useQuery({
    queryKey: ["terminal-command-templates"],
    queryFn: api.fetchTerminalCommandTemplates,
    staleTime: Infinity,
  });
}
