# Implementation Plan

## Files

- **Modify**: `backend/app/models/pipeline.py:40`

## Task 1: Add cascade to PipelineStep.step_runs relationship

**File:** `backend/app/models/pipeline.py` line 40

Change:
```python
step_runs = relationship("PipelineStepRun", back_populates="pipeline_step")
```

To:
```python
step_runs = relationship("PipelineStepRun", back_populates="pipeline_step", cascade="all, delete-orphan")
```

This matches existing patterns in the same file (line 20: `Pipeline.steps`) and in `pipeline_run.py` (line 38: `PipelineRun.step_runs`).

### Verification

1. Start backend and attempt to delete a pipeline step that has existing `PipelineStepRun` records
2. Confirm deletion succeeds (no 500 / IntegrityError)
3. Confirm related `PipelineStepRun` records are removed
