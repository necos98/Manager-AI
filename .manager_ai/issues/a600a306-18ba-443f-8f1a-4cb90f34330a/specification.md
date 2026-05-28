## Problem

`GET /api/pipelines` returns 500 because `PipelineResponse` schema requires `project_id` but the `_response` helper in `pipelines.py` router doesn't include it — and the `Pipeline` model has no `project_id` column at all.

### Error
```
ValidationError: 1 validation error for PipelineResponse
project_id
  Field required [type=missing, ...]
```

## Root Cause

`backend/app/schemas/pipeline.py:29` declares `project_id: str` as required, but:
- `Pipeline` model (`backend/app/models/pipeline.py`) has no `project_id` column
- `PipelineService` has no project-scoping logic
- Router `_response` helper doesn't pass `project_id`
- Frontend doesn't use `project_id` in pipeline responses

## Fix

Remove `project_id` from `PipelineResponse` schema. Pipelines are currently project-agnostic (global).

## Affected Files

- `backend/app/schemas/pipeline.py` — remove `project_id` field from `PipelineResponse`
