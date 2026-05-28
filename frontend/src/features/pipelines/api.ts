import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";
import type { Pipeline, PipelineCreate, PipelineStep, PipelineStepCreate, PipelineUpdate, StepReorderRequest } from "@/shared/types";

export function fetchPipelines(): Promise<Pipeline[]> {
  return apiGet<Pipeline[]>("/pipelines");
}

export function fetchPipeline(pipelineId: string): Promise<Pipeline> {
  return apiGet<Pipeline>(`/pipelines/${pipelineId}`);
}

export function createPipeline(data: PipelineCreate): Promise<Pipeline> {
  return apiPost<Pipeline>("/pipelines", data);
}

export function updatePipeline(pipelineId: string, data: PipelineUpdate): Promise<Pipeline> {
  return apiPut<Pipeline>(`/pipelines/${pipelineId}`, data);
}

export function deletePipeline(pipelineId: string): Promise<null> {
  return apiDelete(`/pipelines/${pipelineId}`);
}

export function addPipelineStep(pipelineId: string, data: PipelineStepCreate): Promise<PipelineStep> {
  return apiPost<PipelineStep>(`/pipelines/${pipelineId}/steps`, data);
}

export function removePipelineStep(pipelineId: string, stepId: string): Promise<null> {
  return apiDelete(`/pipelines/${pipelineId}/steps/${stepId}`);
}

export function reorderPipelineSteps(pipelineId: string, data: StepReorderRequest): Promise<PipelineStep[]> {
  return apiPut<PipelineStep[]>(`/pipelines/${pipelineId}/steps/reorder`, data);
}

export function seedPipeline(): Promise<Pipeline> {
  return apiPost<Pipeline>("/pipelines/seed");
}
