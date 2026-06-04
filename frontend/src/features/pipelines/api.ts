import { apiGet, apiPost, apiPut, apiDelete, buildUrl, uploadRequest } from "@/shared/api/client";
import type { Pipeline, PipelineCreate, PipelineStep, PipelineStepCreate, PipelineUpdate, StepReorderRequest, ImportConfirmResponse, PipelineImportPreviewResponse, PipelineExportItem } from "@/shared/types";

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

export async function exportPipelines(): Promise<Blob> {
  const res = await fetch(buildUrl("/pipelines/export"));
  return res.blob();
}

export async function exportPipeline(pipelineId: string): Promise<Blob> {
  const res = await fetch(buildUrl(`/pipelines/export/${pipelineId}`));
  return res.blob();
}

export function importPipelinesPreview(file: File): Promise<PipelineImportPreviewResponse<PipelineExportItem>> {
  const fd = new FormData();
  fd.append("file", file);
  return uploadRequest<PipelineImportPreviewResponse<PipelineExportItem>>("/pipelines/import/preview", fd);
}

export function importPipelinesConfirm(
  file: File,
  conflicts: Record<string, string>,
): Promise<ImportConfirmResponse> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("conflicts", JSON.stringify(conflicts));
  return uploadRequest<ImportConfirmResponse>("/pipelines/import/confirm", fd);
}
