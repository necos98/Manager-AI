import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { PipelineCreate, PipelineStepCreate, PipelineUpdate, StepReorderRequest } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const pipelineKeys = {
  all: (projectId: string) => ["pipelines", projectId] as const,
  detail: (projectId: string, pipelineId: string) => ["pipelines", projectId, pipelineId] as const,
};

export function usePipelines(projectId: string) {
  return useQuery({
    queryKey: pipelineKeys.all(projectId),
    queryFn: () => api.fetchPipelines(projectId),
    enabled: Boolean(projectId),
  });
}

export function usePipeline(projectId: string, pipelineId: string) {
  return useQuery({
    queryKey: pipelineKeys.detail(projectId, pipelineId),
    queryFn: () => api.fetchPipeline(projectId, pipelineId),
    enabled: Boolean(projectId) && Boolean(pipelineId),
  });
}

export function useCreatePipeline(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PipelineCreate) => api.createPipeline(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useUpdatePipeline(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, data }: { pipelineId: string; data: PipelineUpdate }) =>
      api.updatePipeline(projectId, pipelineId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useDeletePipeline(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (pipelineId: string) => api.deletePipeline(projectId, pipelineId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useAddPipelineStep(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, data }: { pipelineId: string; data: PipelineStepCreate }) =>
      api.addPipelineStep(projectId, pipelineId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useRemovePipelineStep(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, stepId }: { pipelineId: string; stepId: string }) =>
      api.removePipelineStep(projectId, pipelineId, stepId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useReorderPipelineSteps(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, data }: { pipelineId: string; data: StepReorderRequest }) =>
      api.reorderPipelineSteps(projectId, pipelineId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useSeedPipeline(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.seedPipeline(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}
