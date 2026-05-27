# Implementation Plan: Frontend TypeScript types + API layer + hooks

**Goal:** Create TypeScript types, API client functions, and React Query hooks for Agents, Pipelines, and Pipeline Runs — mirroring backend schemas and following the terminals feature pattern.

**Architecture:** Types added to `frontend/src/shared/types/index.ts`. Three feature directories (`agents/`, `pipelines/`, `pipeline-runs/`) each with `api.ts` (REST client functions) and `hooks.ts` (React Query wrappers). All follow the exact same patterns as the existing `terminals` feature.

**Tech Stack:** TypeScript, React Query (`@tanstack/react-query`), shared API client (`@/shared/api/client`)

---

## File changes

| Action | File |
|--------|------|
| Modify | `frontend/src/shared/types/index.ts` |
| Create | `frontend/src/features/agents/api.ts` |
| Create | `frontend/src/features/agents/hooks.ts` |
| Create | `frontend/src/features/pipelines/api.ts` |
| Create | `frontend/src/features/pipelines/hooks.ts` |
| Create | `frontend/src/features/pipeline-runs/api.ts` |
| Create | `frontend/src/features/pipeline-runs/hooks.ts` |

---

## Backend status enums (exact values)

- `PipelineRunStatus`: `"RUNNING" | "COMPLETED" | "FAILED"`
- `PipelineStepRunStatus`: `"PENDING" | "RUNNING" | "COMPLETED" | "FAILED"`

---

## Types to add (shared/types/index.ts)

```typescript
// ── Agent ──

export interface Agent {
  id: string;
  project_id: string;
  name: string;
  system_prompt: string;
  model: string | null;
  allowed_tools: string[] | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentCreate {
  name: string;
  system_prompt: string;
  model?: string | null;
  allowed_tools?: string[] | null;
}

export interface AgentUpdate {
  name?: string;
  system_prompt?: string;
  model?: string | null;
  allowed_tools?: string[] | null;
}

// ── Pipeline ──

export interface PipelineStep {
  id: string;
  pipeline_id: string;
  agent_id: string;
  order_index: number;
  terminal_command: string;
}

export interface PipelineStepCreate {
  agent_id: string;
  order_index?: number;
  terminal_command?: string;
}

export interface Pipeline {
  id: string;
  project_id: string;
  name: string;
  steps: PipelineStep[];
  created_at: string | null;
  updated_at: string | null;
}

export interface PipelineCreate {
  name: string;
  steps?: PipelineStepCreate[];
}

export interface PipelineUpdate {
  name: string;
}

export interface StepReorderRequest {
  step_ids: string[];
}

// ── Pipeline Run ──

export type PipelineRunStatus = "RUNNING" | "COMPLETED" | "FAILED";

export type PipelineStepRunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface PipelineStepRun {
  id: string;
  pipeline_run_id: string;
  pipeline_step_id: string;
  agent_name: string;
  status: PipelineStepRunStatus;
  started_at: string | null;
  finished_at: string | null;
}

export interface PipelineRun {
  id: string;
  pipeline_id: string;
  issue_id: string;
  status: PipelineRunStatus;
  current_step_index: number;
  steps: PipelineStepRun[];
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export interface PipelineRunStart {
  pipeline_id: string;
  issue_id: string;
}

// ── Pipeline Message ──

export interface PipelineMessage {
  id: string;
  pipeline_run_id: string;
  sender_agent_name: string;
  content: string;
  created_at: string | null;
}

export interface PipelineMessageCreate {
  sender_agent_name: string;
  content: string;
}
```

---

## agents/api.ts

```typescript
import { apiGet, apiPost, apiPut, apiDelete } from "@/shared/api/client";
import type { Agent, AgentCreate, AgentUpdate } from "@/shared/types";

export function fetchAgents(projectId: string): Promise<Agent[]> {
  return apiGet<Agent[]>(`/projects/${projectId}/agents`);
}

export function fetchAgent(projectId: string, agentId: string): Promise<Agent> {
  return apiGet<Agent>(`/projects/${projectId}/agents/${agentId}`);
}

export function createAgent(projectId: string, data: AgentCreate): Promise<Agent> {
  return apiPost<Agent>(`/projects/${projectId}/agents`, data);
}

export function updateAgent(projectId: string, agentId: string, data: AgentUpdate): Promise<Agent> {
  return apiPut<Agent>(`/projects/${projectId}/agents/${agentId}`, data);
}

export function deleteAgent(projectId: string, agentId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/agents/${agentId}`);
}

export function seedAgents(projectId: string): Promise<Agent[]> {
  return apiPost<Agent[]>(`/projects/${projectId}/agents/seed`);
}
```

---

## agents/hooks.ts

```typescript
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
```

---

## pipelines/api.ts

```typescript
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
```

---

## pipelines/hooks.ts

```typescript
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
```

---

## pipeline-runs/api.ts

```typescript
import { apiGet, apiPost, apiDelete } from "@/shared/api/client";
import type { PipelineMessage, PipelineMessageCreate, PipelineRun, PipelineRunStart } from "@/shared/types";

export function startPipelineRun(projectId: string, data: PipelineRunStart): Promise<PipelineRun> {
  return apiPost<PipelineRun>(`/projects/${projectId}/pipeline-runs`, data);
}

export function fetchPipelineRuns(projectId: string, issueId: string): Promise<PipelineRun[]> {
  return apiGet<PipelineRun[]>(`/projects/${projectId}/pipeline-runs?issue_id=${encodeURIComponent(issueId)}`);
}

export function fetchPipelineRun(projectId: string, runId: string): Promise<PipelineRun> {
  return apiGet<PipelineRun>(`/projects/${projectId}/pipeline-runs/${runId}`);
}

export function cancelPipelineRun(projectId: string, runId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/pipeline-runs/${runId}`);
}

export function fetchPipelineMessages(projectId: string, runId: string): Promise<PipelineMessage[]> {
  return apiGet<PipelineMessage[]>(`/projects/${projectId}/pipeline-runs/${runId}/messages`);
}

export function sendPipelineMessage(projectId: string, runId: string, data: PipelineMessageCreate): Promise<PipelineMessage> {
  return apiPost<PipelineMessage>(`/projects/${projectId}/pipeline-runs/${runId}/messages`, data);
}
```

---

## pipeline-runs/hooks.ts

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "./api";
import type { PipelineMessageCreate, PipelineRunStart } from "@/shared/types";

const onMutationError = (e: unknown) => {
  toast.error(e instanceof Error ? e.message : "Operation failed");
};

export const pipelineRunKeys = {
  all: (projectId: string) => ["pipeline-runs", projectId] as const,
  byIssue: (projectId: string, issueId: string) => ["pipeline-runs", projectId, "issue", issueId] as const,
  detail: (projectId: string, runId: string) => ["pipeline-runs", projectId, runId] as const,
  messages: (projectId: string, runId: string) => ["pipeline-runs", projectId, runId, "messages"] as const,
};

export function usePipelineRuns(projectId: string, issueId: string) {
  return useQuery({
    queryKey: pipelineRunKeys.byIssue(projectId, issueId),
    queryFn: () => api.fetchPipelineRuns(projectId, issueId),
    enabled: Boolean(projectId) && Boolean(issueId),
  });
}

export function usePipelineRun(projectId: string, runId: string) {
  return useQuery({
    queryKey: pipelineRunKeys.detail(projectId, runId),
    queryFn: () => api.fetchPipelineRun(projectId, runId),
    enabled: Boolean(projectId) && Boolean(runId),
  });
}

export function useStartPipelineRun(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PipelineRunStart) => api.startPipelineRun(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineRunKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function useCancelPipelineRun(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.cancelPipelineRun(projectId, runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineRunKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}

export function usePipelineMessages(projectId: string, runId: string) {
  return useQuery({
    queryKey: pipelineRunKeys.messages(projectId, runId),
    queryFn: () => api.fetchPipelineMessages(projectId, runId),
    enabled: Boolean(projectId) && Boolean(runId),
  });
}

export function useSendPipelineMessage(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, data }: { runId: string; data: PipelineMessageCreate }) =>
      api.sendPipelineMessage(projectId, runId, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: pipelineRunKeys.messages(projectId, variables.runId) });
    },
    onError: onMutationError,
  });
}
```

---

## Verification

```bash
cd frontend
npx tsc --noEmit   # TypeScript compilation check
npm run lint        # ESLint check
```
