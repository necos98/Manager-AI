# Specification: Frontend TypeScript types + API layer + hooks

## Goal

Create TypeScript types, API client functions, and React Query hooks for Agents, Pipelines, and Pipeline Runs — mirroring the backend schemas and following existing frontend patterns (terminals feature).

## Feature directories

Three separate feature directories, matching backend router separation:

1. `frontend/src/features/agents/` — api.ts, hooks.ts
2. `frontend/src/features/pipelines/` — api.ts, hooks.ts
3. `frontend/src/features/pipeline-runs/` — api.ts, hooks.ts

## Shared Types (`frontend/src/shared/types/index.ts`)

Add the following types, mirroring backend Pydantic schemas exactly:

### Agent types
- `Agent` — { id, project_id, name, system_prompt, model, allowed_tools, created_at, updated_at }
- `AgentCreate` — { name, system_prompt, model?, allowed_tools? }
- `AgentUpdate` — { name?, system_prompt?, model?, allowed_tools? }

### Pipeline types
- `PipelineStep` — { id, pipeline_id, agent_id, order_index, terminal_command }
- `PipelineStepCreate` — { agent_id, order_index?, terminal_command? }
- `Pipeline` — { id, project_id, name, steps, created_at, updated_at }
- `PipelineCreate` — { name, steps? }
- `PipelineUpdate` — { name }
- `StepReorderRequest` — { step_ids }

### Pipeline Run types
- `PipelineRunStatus` — "pending" | "running" | "completed" | "failed" | "cancelled"
- `PipelineStepRunStatus` — same union as PipelineRunStatus
- `PipelineStepRun` — { id, pipeline_run_id, pipeline_step_id, agent_name, status, started_at?, finished_at? }
- `PipelineRun` — { id, pipeline_id, issue_id, status, current_step_index, steps, started_at?, finished_at?, created_at? }
- `PipelineRunStart` — { pipeline_id, issue_id }

### Pipeline Message types
- `PipelineMessage` — { id, pipeline_run_id, sender_agent_name, content, created_at? }
- `PipelineMessageCreate` — { sender_agent_name, content }

## API Layer

Each feature's `api.ts` uses the shared API client (`apiGet`, `apiPost`, `apiPut`, `apiDelete` from `@/shared/api/client`). All endpoints are scoped under `/api/projects/{project_id}/`.

### agents/api.ts
| Function | Method | Path |
|----------|--------|------|
| fetchAgents | GET | /api/projects/{pid}/agents |
| fetchAgent | GET | /api/projects/{pid}/agents/{id} |
| createAgent | POST | /api/projects/{pid}/agents |
| updateAgent | PUT | /api/projects/{pid}/agents/{id} |
| deleteAgent | DELETE | /api/projects/{pid}/agents/{id} |
| seedAgents | POST | /api/projects/{pid}/agents/seed |

### pipelines/api.ts
| Function | Method | Path |
|----------|--------|------|
| fetchPipelines | GET | /api/projects/{pid}/pipelines |
| fetchPipeline | GET | /api/projects/{pid}/pipelines/{id} |
| createPipeline | POST | /api/projects/{pid}/pipelines |
| updatePipeline | PUT | /api/projects/{pid}/pipelines/{id} |
| deletePipeline | DELETE | /api/projects/{pid}/pipelines/{id} |
| addPipelineStep | POST | /api/projects/{pid}/pipelines/{id}/steps |
| removePipelineStep | DELETE | /api/projects/{pid}/pipelines/{id}/steps/{step_id} |
| reorderPipelineSteps | PUT | /api/projects/{pid}/pipelines/{id}/steps/reorder |
| seedPipeline | POST | /api/projects/{pid}/pipelines/seed |

### pipeline-runs/api.ts
| Function | Method | Path |
|----------|--------|------|
| startPipelineRun | POST | /api/projects/{pid}/pipeline-runs |
| fetchPipelineRuns | GET | /api/projects/{pid}/pipeline-runs?issue_id= |
| fetchPipelineRun | GET | /api/projects/{pid}/pipeline-runs/{id} |
| cancelPipelineRun | DELETE | /api/projects/{pid}/pipeline-runs/{id} |
| fetchPipelineMessages | GET | /api/projects/{pid}/pipeline-runs/{id}/messages |
| sendPipelineMessage | POST | /api/projects/{pid}/pipeline-runs/{id}/messages |

## React Query Hooks

Each feature's `hooks.ts` follows the terminals pattern:
- Query key factory object with `all` base key and scoped keys
- `useQuery` hooks for read endpoints
- `useMutation` hooks for write endpoints with `invalidateQueries` on success
- `onError` handler using `toast.error` from sonner (same as terminals)
- Default `staleTime: Infinity` for seed/config-like endpoints

### agents/hooks.ts
- `agentKeys` — query key factory
- `useAgents(projectId)` — list agents
- `useAgent(projectId, agentId)` — single agent
- `useCreateAgent(projectId)` — mutation
- `useUpdateAgent(projectId)` — mutation
- `useDeleteAgent(projectId)` — mutation
- `useSeedAgents(projectId)` — mutation

### pipelines/hooks.ts
- `pipelineKeys` — query key factory
- `usePipelines(projectId)` — list pipelines
- `usePipeline(projectId, pipelineId)` — single pipeline
- `useCreatePipeline(projectId)` — mutation
- `useUpdatePipeline(projectId)` — mutation
- `useDeletePipeline(projectId)` — mutation
- `useAddPipelineStep(projectId)` — mutation
- `useRemovePipelineStep(projectId)` — mutation
- `useReorderPipelineSteps(projectId)` — mutation
- `useSeedPipeline(projectId)` — mutation

### pipeline-runs/hooks.ts
- `pipelineRunKeys` — query key factory
- `usePipelineRuns(projectId, issueId)` — list runs for issue
- `usePipelineRun(projectId, runId)` — single run
- `useStartPipelineRun(projectId)` — mutation
- `useCancelPipelineRun(projectId)` — mutation
- `usePipelineMessages(projectId, runId)` — messages for run
- `useSendPipelineMessage(projectId, runId)` — mutation

## Error Handling

- Use same `onMutationError` pattern from terminals: `toast.error(e instanceof Error ? e.message : "Operation failed")`
- HTTP errors handled by shared API client (`ApiError` class)
- 30-second timeout from shared client applies

## Testing

- Verify TypeScript compilation: `cd frontend && npx tsc --noEmit`
- Verify ESLint: `cd frontend && npm run lint`
- Types must match backend schemas exactly (field names, optionality, union values)