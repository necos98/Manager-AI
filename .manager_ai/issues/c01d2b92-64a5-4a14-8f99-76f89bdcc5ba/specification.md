## Root Cause

`Pipeline.runs` relationship (pipeline.py:21) has no cascade setting. When deleting a Pipeline, SQLAlchemy defaults to detaching child `PipelineRun` records by setting `pipeline_id = NULL` (an UPDATE), but `pipeline_runs.pipeline_id` is `nullable=False`, causing `NOT NULL constraint failed`.

Same bug class previously hit on `PipelineStep.step_runs` — documented in memory `6e2ccbe6`.

## Fix

Add `cascade="all, delete-orphan"` to `Pipeline.runs` relationship in `backend/app/models/pipeline.py:21`:

```python
# Before
runs = relationship("PipelineRun", back_populates="pipeline")

# After
runs = relationship("PipelineRun", back_populates="pipeline", cascade="all, delete-orphan")
```

This cascades deletion: Pipeline → PipelineRun → PipelineStepRun + PipelineMessage. The child cascades for `PipelineRun.step_runs` and `PipelineRun.messages` are already configured.

## Impact

- Deleting a pipeline now also deletes all its runs, step runs, and messages
- No schema migration needed (relationship-level change only)
- Matches existing cascade pattern used by `Pipeline.steps`, `PipelineRun.step_runs`, `PipelineRun.messages`