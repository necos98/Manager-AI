## CodeReview Recap: Show pipeline name when running on issue

**Spec**: Display pipeline name in 2 places when pipeline is RUNNING on an issue — issue detail page badge + kanban card indicator. Batch endpoint to avoid N+1 on kanban.

**What was built**:
- **Backend**: `GET /api/pipeline-runs/active-by-issue?issue_ids=...` endpoint returning `{issue_id: {pipeline_name, status} | null}`. Single query with eager-loaded pipeline relationship. `ActivePipelineRunResponse` schema.
- **Frontend types**: `pipeline_name: string` added to `PipelineRun` TS interface.
- **Frontend API/hooks**: `fetchActivePipelineRuns()` + `useActivePipelineRuns()` hook with 5s polling.
- **Issue detail page**: Blue-tinted outline badge "Pipeline: {name}" shown near StatusBadge when RUNNING run exists.
- **PipelineProgress**: Header shows real pipeline name instead of hardcoded "Pipeline".
- **Kanban cards**: Blue dot + truncated pipeline name in card metadata. Prop-drilled from IssuesPage → KanbanBoard → KanbanColumn → KanbanCard.

**Review outcome**: PASS — no high-priority issues. 182 tests pass (1 pre-existing failure in test_db_backup, unrelated). Code is correct, secure, and aligned with spec and project conventions.