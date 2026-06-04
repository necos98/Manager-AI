## Scope

Add rejection/feedback-loop capability to Agent Pipeline. Review steps (CodeReviewer, QualityReviewer, SpecReviewer, PlanReviewer) can reject code/spec/plan instead of just passing. Pipeline loops back to the appropriate previous step for fixes instead of advancing linearly.

## Why

Current pipelines are strictly linear. Each step calls `finished_pipeline_step` and the next agent activates. Reviewers have no way to say "this fails quality gate — send it back." Reviews are advisory only. This renders CodeReviewer, QualityReviewer, SpecReviewer, and PlanReviewer toothless.

## Requirements

### 1. New status: REJECTED

Add `REJECTED` to pipeline step run statuses (alongside PENDING, RUNNING, COMPLETED). Only review-type agents (SpecReviewer, PlanReviewer, CodeReviewer, QualityReviewer) can set this.

### 2. API: finished_pipeline_step extended

Extend the existing `finished_pipeline_step` MCP tool with optional rejection fields — this is the **single entry point** for both completion and rejection:

```
finished_pipeline_step(issue_id, summary, rejected=False, rejection_reason=None, target_step_index=None)
```

When `rejected=True`, the tool:
- Sets the current step run status to `REJECTED`
- Creates a **new** RUNNING step run for the target step (never re-activates old runs — preserves history)
- Pipeline regresses to the target step
- Stores the rejection reason in pipeline messages for the target agent

No separate `reject_step` MCP tool needed — `finished_pipeline_step` handles both paths.

### 3. Loop guard

- Max N rejections per pipeline run (configurable, default 3)
- After N rejections, pipeline moves to a FAILED terminal state
- Prevents infinite feedback loops

### 4. Context preservation

When a step is rejected and the pipeline returns to Developer (or PlanWriter):
- The rejection reason is delivered via pipeline messages (existing `send_agent_message` / `get_pipeline_messages` mechanisms)
- Rejected agent sees which step rejected and why
- Full context of previous work preserved (no state loss)

### 5. Terminal states

Pipeline run gains a new terminal state:
- **FAILED** — max rejections exceeded or unrecoverable rejection
- Existing **COMPLETED** and **CANCELLED** states remain unchanged

### 6. Backend: reject_step service method

Add a `reject_step()` method to `PipelineRunService`:
- Parameters: current step_run_id, reason (string), target_step_index (0-based index into pipeline steps array)
- Sets current step to `REJECTED`
- Creates new PipelineStepRun with RUNNING status for the target step
- Increments `rejection_count` on PipelineRun
- Triggers WebSocket event on rejection
- The `_execute()` loop must change from sequential `for` to a `while` loop driven by `current_step_index` to support regression

### 7. Event emission

Emit real-time WebSocket event on rejection so frontend can display rejection in the pipeline UI. Event name: `pipeline_step_rejected`, payload includes: `run_id`, `step_run_id`, `agent_name`, `reason`, `target_step_index`, `project_id`.

## Acceptance Criteria

1. Review agents can reject a pipeline step with a reason and target step, causing the pipeline to regress instead of advance.
2. Rejected steps are recorded in the database with `REJECTED` status.
3. Pipeline runs track rejection count and fail after 3 rejections (configurable).
4. When regressing, a new step run is created for the target step (fresh RUNNING status, preserving rejection history).
5. The rejection reason is available to the target agent via pipeline messages.
6. The `finished_pipeline_step` MCP tool accepts the `rejected` parameter — when `rejected=True`, it triggers the rejection flow; when `rejected=False` (default), it completes the step as before.
7. A WebSocket event named `pipeline_step_rejected` fires on each rejection with run_id, step_run_id, agent_name, reason, target_step_index, and project_id.
8. No existing pipeline functionality is broken (backward compatible).

## Non-goals

- Automatic partial rollback (undoing git changes). Developer receives rejection context and fixes manually.
- Multiple parallel rejection targets. One rejection targets one step.
- UI for rejection flow beyond events — frontend work is minimal and limited to event display.
- Changes to agent behavior or review criteria — only the pipeline mechanics change.
