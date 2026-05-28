## Fix

Added `cascade="all, delete-orphan"` to `Pipeline.runs` relationship in `backend/app/models/pipeline.py:21`.

**Root cause:** Deleting a Pipeline with existing PipelineRun records triggered SQLAlchemy's default detach behavior — setting `pipeline_id=NULL` via UPDATE — which violated the NOT NULL constraint on `pipeline_runs.pipeline_id`.

**Change:** One-line addition: `cascade="all, delete-orphan"` on the `runs` relationship. This cascades deletion: Pipeline → PipelineRun → PipelineStepRun + PipelineMessage. The child cascades were already configured.

**Same bug class** as memory `6e2ccbe6` (PipelineStep.step_runs cascade fix). Pattern: any deletable parent with a non-nullable FK child relationship needs explicit cascade.