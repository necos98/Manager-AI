import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { PipelineCreate, PipelineStepCreate, PipelineUpdate, StepReorderRequest } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const pipelineKeys = {
  all: () => ["pipelines"] as const,
  detail: (pipelineId: string) => ["pipelines", pipelineId] as const,
};

export function usePipelines() {
  return useQuery({
    queryKey: pipelineKeys.all(),
    queryFn: () => api.fetchPipelines(),
  });
}

export function usePipeline(pipelineId: string) {
  return useQuery({
    queryKey: pipelineKeys.detail(pipelineId),
    queryFn: () => api.fetchPipeline(pipelineId),
    enabled: Boolean(pipelineId),
  });
}

export function useCreatePipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PipelineCreate) => api.createPipeline(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useUpdatePipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, data }: { pipelineId: string; data: PipelineUpdate }) =>
      api.updatePipeline(pipelineId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useDeletePipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (pipelineId: string) => api.deletePipeline(pipelineId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useAddPipelineStep() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, data }: { pipelineId: string; data: PipelineStepCreate }) =>
      api.addPipelineStep(pipelineId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useRemovePipelineStep() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, stepId }: { pipelineId: string; stepId: string }) =>
      api.removePipelineStep(pipelineId, stepId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useReorderPipelineSteps() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, data }: { pipelineId: string; data: StepReorderRequest }) =>
      api.reorderPipelineSteps(pipelineId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useSeedPipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.seedPipeline(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}
