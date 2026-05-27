import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { AgentCreate, AgentUpdate } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const agentKeys = {
  all: (projectId: string) => ["agents", projectId] as const,
  detail: (projectId: string, agentId: string) => ["agents", projectId, agentId] as const,
};

export function useAgents(projectId: string) {
  return useQuery({
    queryKey: agentKeys.all(projectId),
    queryFn: () => api.fetchAgents(projectId),
    enabled: Boolean(projectId),
  });
}

export function useAgent(projectId: string, agentId: string) {
  return useQuery({
    queryKey: agentKeys.detail(projectId, agentId),
    queryFn: () => api.fetchAgent(projectId, agentId),
    enabled: Boolean(projectId) && Boolean(agentId),
  });
}

export function useCreateAgent(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AgentCreate) => api.createAgent(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useUpdateAgent(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, data }: { agentId: string; data: AgentUpdate }) =>
      api.updateAgent(projectId, agentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useDeleteAgent(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => api.deleteAgent(projectId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useSeedAgents(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.seedAgents(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}
