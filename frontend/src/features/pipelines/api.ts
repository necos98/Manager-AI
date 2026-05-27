import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";
import type { Pipeline, PipelineCreate, PipelineStep, PipelineStepCreate, PipelineUpdate, StepReorderRequest } from "@/shared/types";

export function fetchPipelines(projectId: string): Promise<Pipeline[]> {
  return apiGet<Pipeline[]>(`/projects/${projectId}/pipelines`);
}

export function fetchPipeline(projectId: string, pipelineId: string): Promise<Pipeline> {
  return apiGet<Pipeline>(`/projects/${projectId}/pipelines/${pipelineId}`);
}

export function createPipeline(projectId: string, data: PipelineCreate): Promise<Pipeline> {
  return apiPost<Pipeline>(`/projects/${projectId}/pipelines`, data);
}

export function updatePipeline(projectId: string, pipelineId: string, data: PipelineUpdate): Promise<Pipeline> {
  return apiPut<Pipeline>(`/projects/${projectId}/pipelines/${pipelineId}`, data);
}

export function deletePipeline(projectId: string, pipelineId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/pipelines/${pipelineId}`);
}

export function addPipelineStep(projectId: string, pipelineId: string, data: PipelineStepCreate): Promise<PipelineStep> {
  return apiPost<PipelineStep>(`/projects/${projectId}/pipelines/${pipelineId}/steps`, data);
}

export function removePipelineStep(projectId: string, pipelineId: string, stepId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/pipelines/${pipelineId}/steps/${stepId}`);
}

export function reorderPipelineSteps(projectId: string, pipelineId: string, data: StepReorderRequest): Promise<PipelineStep[]> {
  return apiPut<PipelineStep[]>(`/projects/${projectId}/pipelines/${pipelineId}/steps/reorder`, data);
}

export function seedPipeline(projectId: string): Promise<Pipeline> {
  return apiPost<Pipeline>(`/projects/${projectId}/pipelines/seed`);
}
