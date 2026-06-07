## Spec: Pipeline stall when PlanWriter calls accept_issue without finished_pipeline_step

### Problem
PlanWriter agent had `accept_issue` in its intent text and `allowed_tools`. When PlanWriter calls `accept_issue` as its terminal action, the pipeline orchestrator's `_run_step()` blocks forever waiting for `finished_pipeline_step` (1800s timeout). The issue transitions to ACCEPTED but the pipeline run stays RUNNING, then times out to FAILED — inconsistent state.

Root cause: lifecycle state transitions (`accept_issue`, `complete_issue`) are orthogonal to pipeline step completion (`finished_pipeline_step`). Agents that call `accept_issue` as a terminal action never call `finished_pipeline_step`, which is the only signal `_run_step()` recognizes as successful step completion.

### Current state
- PlanWriter intent text in DB already cleaned of `accept_issue` reference (updated 2026-06-05T14:20:27)
- PlanWriter `allowed_tools` still includes `accept_issue`
- Code DEFAULT_AGENTS seed is already clean (no `accept_issue`)
- Memory `de943f40` documents the policy: no lifecycle transitions in agent intents
- Memory `cb0b9511` documents the asyncio.Event gating mechanism

### Changes

#### 1. Remove `accept_issue` from PlanWriter's allowed_tools
- Prevents PlanWriter from calling `accept_issue` even if intent text changes
- Lifecycle management belongs to /run-pipeline command, not individual agents
- File: `backend/app/services/agent_service.py` — DEFAULT_AGENTS PlanWriter entry (remove from allowed_tools if present)
- Also: update DB agent record via `update_agent` MCP tool

#### 2. Defensive fix in finished_pipeline_step
- When `finish_step()` cannot find an active step run for the issue, check if issue status is ACCEPTED
- If ACCEPTED → log warning and return success (the step implicitly completed via state transition)
- This prevents stalls even if the pattern recurs through another path
- File: `backend/app/services/pipeline_run_service.py` — `finish_step()` method

### Non-goals
- No changes to `agent_service.py` DEFAULT_AGENTS seed (already clean)
- No changes to `_run_step()` three-way wait mechanism
- No changes to `accept_issue` MCP tool itself

### Acceptance criteria
1. PlanWriter agent no longer has `accept_issue` in allowed_tools
2. Calling `finished_pipeline_step` when issue is ACCEPTED but no active step run exists returns success (not error)
3. Existing pipeline completion flow (normal path) unchanged
4. All existing tests pass
