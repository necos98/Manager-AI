## Plan

Remove `project_id: str` from `PipelineResponse` in `backend/app/schemas/pipeline.py` line 29.

### Steps
1. Edit `backend/app/schemas/pipeline.py` — remove the `project_id: str` field from `PipelineResponse`
2. Verify fix by checking the model/schema are now consistent
