## Summary

Implemented pipeline full-lifecycle support with SpecWriter agent and Start Pipeline button.

## Changes Made

### Backend — `orchestrator_service.py`
- Added **SpecWriter** agent (5th default) with `role_key="spec_writer"` and detailed system prompt instructing it to call `create_issue_spec`, `create_issue_plan`, `create_plan_tasks`, `send_agent_message`, and `complete_agent_step`
- Updated `ensure_default_pipeline()` role_order to 5 steps: `["spec_writer", "architect", "developer", "reviewer", "qa"]`
- Added `ROLE_ORDER` class constant and `_get_starting_step_index()` method for intelligent step skipping based on issue state:
  - NEW → start from spec_writer (index 0)
  - REASONING → skip spec_writer, start from architect (index 1)
  - PLANNED/ACCEPTED → skip spec_writer+architect, start from developer (index 2)
- Modified `start_pipeline()` to skip already-completed steps and added duplicate prevention (checks for existing RUNNING pipeline before creating new)

### Backend — `issues.py` router
- Added `POST /api/projects/{project_id}/issues/{issue_id}/start-pipeline` endpoint that delegates to OrchestratorService

### Backend — Migration
- Deleted broken migration `6fbb705de97e` (empty upgrade) and updated `04f837ab5823` down_revision chain: `6fbb705de97e` → `9a752a193fcf`

### Frontend — `issue-actions.tsx`
- Added **Start Pipeline** button with GitBranch icon, visible for all non-terminal issue states
- Button shows "Pipeline Running" when a pipeline is already active (disable duplicate starts)
- Added `useStartPipeline` and `usePipelineRunsForIssue` hook integration

### Frontend — `api.ts` + `hooks.ts`
- Added `startPipeline()` API function and `useStartPipeline()` mutation hook with cache invalidation and toast notifications

### Tests — `test_orchestrator.py`
- Updated existing tests from 4→5 agents/steps
- Added 5 new tests: `test_start_pipeline_from_new_state`, `test_start_pipeline_from_reasoning_state`, `test_start_pipeline_from_planned_state`, `test_start_pipeline_duplicate_prevented`, `test_spec_writer_system_prompt`
- All 37 tests pass

## Key Decisions
- Duplicate pipeline prevention: `start_pipeline()` returns `None` (not an error) when a RUNNING pipeline already exists. The REST endpoint returns an error message; frontend shows "Pipeline Running" disabled button.
- When `accept_issue` auto-triggers pipeline for a Planned issue, pipeline starts from developer (3 steps) since spec+plan already exist.
- The changes were applied to both the working directory (`manager-ai-mod/Manager-AI`) and the venv-linked directory (`Manager-AI`) since Python imports from the latter.