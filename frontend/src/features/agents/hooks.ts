import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  fetchAgents,
  createAgent,
  updateAgent,
  deleteAgent,
  fetchPipelines,
  createPipeline,
  updatePipeline,
  deletePipeline,
  fetchPipelineRun,
  fetchPipelineRunsForIssue,
  startPipeline,
  type AgentData,
} from "./api";

// Agents
export function useAgents(projectId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "agents"],
    queryFn: () => fetchAgents(projectId),
    enabled: !!projectId,
  });
}

export function useCreateAgent(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; role_key: string; system_prompt?: string }) =>
      createAgent(projectId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "agents"] });
      toast.success("Agent created");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useUpdateAgent(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ agentId, data }: { agentId: string; data: Record<string, unknown> }) =>
      updateAgent(projectId, agentId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "agents"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useDeleteAgent(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => deleteAgent(projectId, agentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "agents"] });
      toast.success("Agent deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

// Pipelines
export function usePipelines(projectId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "pipelines"],
    queryFn: () => fetchPipelines(projectId),
    enabled: !!projectId,
  });
}

export function useCreatePipeline(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; steps: { agent_id: string; order: number }[]; is_default?: boolean; trigger_type?: string }) =>
      createPipeline(projectId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "pipelines"] });
      toast.success("Pipeline created");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useUpdatePipeline(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ pipelineId, data }: { pipelineId: string; data: Record<string, unknown> }) =>
      updatePipeline(projectId, pipelineId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "pipelines"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useDeletePipeline(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pipelineId: string) => deletePipeline(projectId, pipelineId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "pipelines"] });
      toast.success("Pipeline deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

// Pipeline Runs
export function usePipelineRun(runId: string | null) {
  return useQuery({
    queryKey: ["pipeline-runs", runId],
    queryFn: () => fetchPipelineRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const data = query.state.data as PipelineRunFullData | undefined;
      if (!data) return false;
      return data.run.status === "running" ? 3000 : false;
    },
  });
}

export function usePipelineRunsForIssue(projectId: string, issueId: string | null) {
  return useQuery({
    queryKey: ["projects", projectId, "issues", issueId, "pipeline-runs"],
    queryFn: () => fetchPipelineRunsForIssue(projectId, issueId!),
    enabled: !!projectId && !!issueId,
    refetchInterval: (query) => {
      const data = query.state.data as { runs: PipelineRunData[] } | undefined;
      if (!data) return false;
      return data.runs.some((r) => r.status === "running") ? 3000 : false;
    },
  });
}

export function useStartPipeline(projectId: string, issueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => startPipeline(projectId, issueId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", projectId, "issues", issueId, "pipeline-runs"] });
      toast.success("Pipeline started");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}
