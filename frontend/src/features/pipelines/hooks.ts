import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import { downloadBlob } from "@/shared/utils/download";
import { saveFile } from "@/shared/utils/saveFile";
import type { PipelineCreate, PipelineEventRuleCreate, PipelineStepCreate, PipelineUpdate, StepReorderRequest } from "@/shared/types";

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

export function useExportPipelines() {
  return useMutation({
    mutationFn: () => api.exportPipelines(),
    onSuccess: (blob) => {
      downloadBlob(blob, "pipelines-export.json");
    },
    onError: onMutationError,
  });
}

export function useExportPipeline() {
  return useMutation({
    mutationFn: (pipelineId: string) => api.exportPipeline(pipelineId),
    onSuccess: (blob) => {
      downloadBlob(blob, "pipeline-export.json");
    },
    onError: onMutationError,
  });
}

export function useExportPipelinesBatch() {
  return useMutation({
    mutationFn: (pipelineIds: string[]) => api.exportPipelinesBatch(pipelineIds),
    onSuccess: (blob, pipelineIds) => {
      saveFile(blob, "pipelines-export.json");
      toast.success(`Exported ${pipelineIds.length} pipeline${pipelineIds.length === 1 ? "" : "s"}`);
    },
    onError: onMutationError,
  });
}

export function useImportPipelinesPreview() {
  return useMutation({
    mutationFn: (file: File) => api.importPipelinesPreview(file),
    onError: onMutationError,
  });
}

export function useImportPipelinesConfirm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      conflicts,
    }: {
      file: File;
      conflicts: Record<string, string>;
    }) => api.importPipelinesConfirm(file, conflicts),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useEventRules(pipelineId: string) {
  return useQuery({
    queryKey: [...pipelineKeys.detail(pipelineId), "event-rules"],
    queryFn: () => api.fetchEventRules(pipelineId),
    enabled: Boolean(pipelineId),
  });
}

export function useCreateEventRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, data }: { pipelineId: string; data: PipelineEventRuleCreate }) =>
      api.createEventRule(pipelineId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useDeleteEventRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, ruleId }: { pipelineId: string; ruleId: string }) =>
      api.deleteEventRule(pipelineId, ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}

export function useUpdateEventRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      pipelineId,
      ruleId,
      data,
    }: {
      pipelineId: string;
      ruleId: string;
      data: Partial<PipelineEventRuleCreate>;
    }) => api.updateEventRule(pipelineId, ruleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.all() });
    },
    onError: onMutationError,
  });
}
