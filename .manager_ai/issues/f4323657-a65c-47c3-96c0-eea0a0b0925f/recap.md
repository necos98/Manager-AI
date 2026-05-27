## Summary

Added TypeScript types, API client functions, and React Query hooks for Agents, Pipelines, and Pipeline Runs to the frontend.

## Files changed

- **Modified:** `frontend/src/shared/types/index.ts` — Added Agent, AgentCreate, AgentUpdate, PipelineStep, PipelineStepCreate, Pipeline, PipelineCreate, PipelineUpdate, StepReorderRequest, PipelineRunStatus, PipelineStepRunStatus, PipelineStepRun, PipelineRun, PipelineRunStart, PipelineMessage, PipelineMessageCreate types
- **Created:** `frontend/src/features/agents/api.ts` — fetchAgents, fetchAgent, createAgent, updateAgent, deleteAgent, seedAgents
- **Created:** `frontend/src/features/agents/hooks.ts` — useAgents, useAgent, useCreateAgent, useUpdateAgent, useDeleteAgent, useSeedAgents
- **Created:** `frontend/src/features/pipelines/api.ts` — fetchPipelines, fetchPipeline, createPipeline, updatePipeline, deletePipeline, addPipelineStep, removePipelineStep, reorderPipelineSteps, seedPipeline
- **Created:** `frontend/src/features/pipelines/hooks.ts` — usePipelines, usePipeline, useCreatePipeline, useUpdatePipeline, useDeletePipeline, useAddPipelineStep, useRemovePipelineStep, useReorderPipelineSteps, useSeedPipeline
- **Created:** `frontend/src/features/pipeline-runs/api.ts` — startPipelineRun, fetchPipelineRuns, fetchPipelineRun, cancelPipelineRun, fetchPipelineMessages, sendPipelineMessage
- **Created:** `frontend/src/features/pipeline-runs/hooks.ts` — usePipelineRuns, usePipelineRun, useStartPipelineRun, useCancelPipelineRun, usePipelineMessages, useSendPipelineMessage

## Verification

- `npx tsc --noEmit` — passed, no errors
- `npm run lint` — pre-existing ESLint parser issue across all TS files; no new issues introduced

## Key decisions

- Feature directories: agents, pipelines, pipeline-runs as separate features (matching backend router separation)
- Status enums use exact backend string values (UPPERCASE): PipelineRunStatus = "RUNNING" | "COMPLETED" | "FAILED", PipelineStepRunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"
- All patterns follow existing terminals feature exactly (query key factories, onMutationError with sonner toast, enabled guards)