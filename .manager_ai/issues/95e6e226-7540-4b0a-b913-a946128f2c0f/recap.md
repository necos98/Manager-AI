## Fix

Added `cascade="all, delete-orphan"` to `PipelineStep.step_runs` relationship in `backend/app/models/pipeline.py:40`.

## Root Cause

When deleting a `PipelineStep`, SQLAlchemy tried to detach related `PipelineStepRun` records by setting `pipeline_step_id=NULL`. The column is `nullable=False`, causing `IntegrityError: NOT NULL constraint failed: pipeline_step_runs.pipeline_step_id`.

## Solution

Cascade delete is consistent with existing patterns:
- `Pipeline.steps` — `cascade="all, delete-orphan"` (pipeline.py:20)
- `PipelineRun.step_runs` — `cascade="all, delete-orphan"` (pipeline_run.py:38)

## Change

One line in `backend/app/models/pipeline.py:40`:
```python
step_runs = relationship("PipelineStepRun", back_populates="pipeline_step", cascade="all, delete-orphan")
```