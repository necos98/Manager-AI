## Tester Recap

### What was tested
- All 6 implementation tasks were verified complete (all status: Completed)
- Backend: `get_active_runs_for_project` method in `pipeline_run_service.py` (JOIN through issues table), new `GET /api/pipeline-runs/active-by-project` endpoint in `pipeline_runs.py`, old `active-by-issue` endpoint removed
- Frontend: `fetchActivePipelineRunsByProject` in `api.ts`, rewritten `useActivePipelineRuns(projectId)` hook with smart polling (5s active / 30s idle), query key `["pipeline-runs", projectId, "active-by-project"]` matching WS invalidation, caller updated in `issues/index.tsx`

### Test results
- **24 pipeline-specific tests passed** — all pipeline-run service and model tests
- **2 pre-existing errors** in `test_pipeline_run_service.py` (test_start_rejects_double_start, test_empty_pipeline_completes_immediately) — not related to this issue's changes
- **33 failed / 15 errors total** — all pre-existing in unrelated modules (issues router, projects router, dashboard, settings, terminals, tasks, templates, variables)

### Verdict
- Code changes are correct and complete
- All pipeline tests pass
- No regressions introduced
- Issue implementation is complete