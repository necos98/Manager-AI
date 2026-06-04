import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { AgentCreate, AgentUpdate } from "@/shared/types";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const agentKeys = {
  all: () => ["agents"] as const,
  detail: (agentId: string) => ["agents", agentId] as const,
};

export function useAgents() {
  return useQuery({
    queryKey: agentKeys.all(),
    queryFn: () => api.fetchAgents(),
  });
}

export function useAgent(agentId: string) {
  return useQuery({
    queryKey: agentKeys.detail(agentId),
    queryFn: () => api.fetchAgent(agentId),
    enabled: Boolean(agentId),
  });
}

export function useCreateAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AgentCreate) => api.createAgent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useUpdateAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, data }: { agentId: string; data: AgentUpdate }) =>
      api.updateAgent(agentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useDeleteAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => api.deleteAgent(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useSeedAgents() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.seedAgents(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useExportAgents() {
  return useMutation({
    mutationFn: () => api.exportAgents(),
    onSuccess: (blob) => {
      downloadBlob(blob, "agents-export.json");
    },
    onError: onMutationError,
  });
}

export function useExportAgent() {
  return useMutation({
    mutationFn: (agentId: string) => api.exportAgent(agentId),
    onSuccess: (blob) => {
      downloadBlob(blob, "agent-export.json");
    },
    onError: onMutationError,
  });
}

export function useImportAgentsPreview() {
  return useMutation({
    mutationFn: (file: File) => api.importAgentsPreview(file),
    onError: onMutationError,
  });
}

export function useImportAgentsConfirm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      conflicts,
    }: {
      file: File;
      conflicts: Record<string, string>;
    }) => api.importAgentsConfirm(file, conflicts),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all() });
    },
    onError: onMutationError,
  });
}
