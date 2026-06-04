# Show Pipeline Name on Running Issues

## Scope

Display the pipeline name when a pipeline is actively running on an issue. Show in two locations: issue detail page and kanban card.

## Requirements

### 1. Issue Detail Page — Pipeline Name Badge

When an issue has a RUNNING pipeline, show the pipeline name as a badge in the header metadata area (between StatusBadge and category selector). Badge format:

- Foreground: pipeline name
- Style: distinct from StatusBadge — use subtle colored background (e.g. blue-tinted to signal "active")
- Shows **only** when pipeline status is RUNNING. Hide when COMPLETED/FAILED.

### 2. Issue Detail Page — PipelineProgress Header

Replace the hardcoded "Pipeline" text in PipelineProgress header with the actual `pipeline_name` from the active PipelineRun.

### 3. Kanban Card — Pipeline Indicator

Show a compact pipeline indicator on kanban cards when the issue has a RUNNING pipeline:

- Small colored dot + pipeline name (truncated if long)
- Placed in the top metadata area, near terminal icon and category badge
- Pipeline run data fetched via batch endpoint (not N+1 per card)

### 4. Batch Endpoint for Kanban

New backend endpoint:

```
GET /api/pipeline-runs/active-by-issue?issue_ids=id1,id2,id3...
Response: { "<issue_id>": { "pipeline_name": "...", "status": "RUNNING" } | null }
```

Returns only RUNNING pipelines. Returns null for issues without an active run.

### 5. Frontend Type Fix

TS interface `PipelineRun` is missing `pipeline_name: string` — add it.

## Constraints

- Show only RUNNING pipelines. Not COMPLETED/FAILED.
- Kanban batch endpoint must avoid N+1 queries.
- Pipeline name in kanban card must not overflow — truncate with ellipsis.
- Pipeline name badge on issue detail is read-only (not editable).

## Acceptance Criteria

- [ ] Issue detail page shows pipeline name badge when pipeline is RUNNING
- [ ] PipelineProgress header shows pipeline name (not "Pipeline")
- [ ] Kanban card shows pipeline indicator when pipeline is RUNNING
- [ ] Kanban does not fetch per-issue — uses batch endpoint
- [ ] No pipeline name shown for COMPLETED/FAILED pipelines
- [ ] TS PipelineRun type includes pipeline_name
- [ ] Existing tests pass

## Non-Goals

- No backend changes to existing PipelineRunResponse schema (already has pipeline_name)
- No changes to pipeline creation or run logic
- No editing pipeline names from issue UI
- No showing pipeline name for finished/failed runs
- No new database migrations