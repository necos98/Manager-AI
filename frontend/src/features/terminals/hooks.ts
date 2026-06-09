import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import { usePipelineRuns } from "@/features/pipeline-runs/hooks";
import type { AskTerminalCreate, LogTerminalCreate, ManageAgentTerminalCreate, TerminalCreate, TerminalCommandUpdate } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const terminalKeys = {
  all: ["terminals"] as const,
  count: ["terminals", "count"] as const,
  config: ["terminals", "config"] as const,
  ask: (projectId: string) => ["terminals", "ask", projectId] as const,
  manageAgent: ["terminals", "manage-agent"] as const,
  commands: (projectId?: string | null) => ["terminal-commands", projectId] as const,
  variables: ["terminal-commands", "variables"] as const,
};

export function useTerminals(projectId?: string, issueId?: string) {
  return useQuery({
    queryKey: [...terminalKeys.all, projectId, issueId] as const,
    queryFn: () => api.fetchTerminals(projectId, issueId),
    refetchInterval: 3000,
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

export function useCreateLogTerminal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: LogTerminalCreate) => api.createLogTerminal(data),
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

export function useCreateManageAgentTerminal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ManageAgentTerminalCreate) => api.createManageAgentTerminal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.all });
      queryClient.invalidateQueries({ queryKey: terminalKeys.count });
      queryClient.invalidateQueries({ queryKey: terminalKeys.manageAgent });
    },
    onError: onMutationError,
  });
}

export function useManageAgentTerminals() {
  return useQuery({
    queryKey: terminalKeys.manageAgent,
    queryFn: api.fetchManageAgentTerminals,
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
      queryClient.invalidateQueries({ queryKey: terminalKeys.manageAgent });
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

export function useTerminalLayout(projectId: string, issueId: string) {
  const { data: terminals } = useTerminals(undefined, issueId);
  const createTerminal = useCreateTerminal();
  const killTerminal = useKillTerminal();
  const { data: countData } = useTerminalCount();
  const { data: configData } = useTerminalConfig();
  const { data: pipelineRuns } = usePipelineRuns(projectId, issueId, { refetchInterval: 3000 });

  const activeRun = pipelineRuns?.find((r) => r.status === "RUNNING") ?? null;
  const terminal1 = terminals?.[0] ?? null;
  const terminal2 = terminals?.[1] ?? null;
  const hasAny = !!terminal1;
  const hasSplit = !!terminal2;

  const [showLimitWarning, setShowLimitWarning] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [rightPanel, setRightPanel] = useState<"terminal" | "pipeline">("terminal");

  const doOpenTerminal = useCallback(async () => {
    setShowLimitWarning(false);
    try {
      await createTerminal.mutateAsync({ issue_id: issueId, project_id: projectId, run_commands: false });
    } catch (err) {
      toast.error("Failed to open terminal: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  }, [createTerminal, issueId, projectId]);

  const openTerminal = useCallback(async () => {
    const count = countData?.count ?? 0;
    const softLimit = configData?.soft_limit ?? 5;
    if (count >= softLimit) { setShowLimitWarning(true); return; }
    await doOpenTerminal();
  }, [countData, configData, doOpenTerminal]);

  const closeAll = useCallback(async () => {
    setShowCloseConfirm(false);
    for (const t of terminals ?? []) {
      try { await killTerminal.mutateAsync(t.id); } catch { /* already dead */ }
    }
  }, [terminals, killTerminal]);

  const handleSessionEnd = useCallback((id: string) => killTerminal.mutate(id), [killTerminal]);
  const handleDownload = useCallback((id: string) => { window.open(`/api/terminals/${id}/recording`); }, []);

  const layoutMode: 'issue-only' | 'issue-pipeline' | 'tabs-mode' | 'single-terminal' = !hasAny && !activeRun ? 'issue-only'
    : !hasAny && activeRun ? 'issue-pipeline'
    : activeRun ? 'tabs-mode'
    : 'single-terminal';

  return {
    terminals, terminal1, terminal2, hasAny, hasSplit,
    activeRun, layoutMode, createTerminal, killTerminal,
    openTerminal, doOpenTerminal, closeAll,
    showLimitWarning, setShowLimitWarning,
    showCloseConfirm, setShowCloseConfirm,
    rightPanel, setRightPanel,
    handleSessionEnd, handleDownload,
    isOpening: createTerminal.isPending,
  };
}

export function useCreateHermesTerminal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (command: string) => api.createHermesTerminal(command),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.all });
      queryClient.invalidateQueries({ queryKey: terminalKeys.count });
    },
    onError: onMutationError,
  });
}
