## Fix

Removed `project_id: str` from `PipelineResponse` in `backend/app/schemas/pipeline.py`.

### Root Cause
`PipelineResponse` required `project_id` but `Pipeline` model has no `project_id` column and the router `_response` helper never passed it. Schema-model mismatch caused 500 on `GET /api/pipelines`.

### Change
- `backend/app/schemas/pipeline.py:29` — removed `project_id: str` field from `PipelineResponse`