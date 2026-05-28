# Fix pipeline step deletion: NOT NULL constraint on pipeline_step_runs.pipeline_step_id

## Problem

Deleting a pipeline step (DELETE `/api/projects/{id}/pipelines/{id}/steps/{id}`) fails with 500:

```
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: pipeline_step_runs.pipeline_step_id
[SQL: UPDATE pipeline_step_runs SET pipeline_step_id=? WHERE pipeline_step_runs.id = ?]
[parameters: [(None, '150ab25b-...'), (None, '158cbdc0-...'), ...]]
```

## Root Cause

`PipelineStep.step_runs` relationship (`backend/app/models/pipeline.py:40`) has no `cascade` setting:

```python
step_runs = relationship("PipelineStepRun", back_populates="pipeline_step")
```

When SQLAlchemy deletes a `PipelineStep`, it defaults to detaching child `PipelineStepRun` records by setting `pipeline_step_id=NULL`. But the column is `nullable=False` (`backend/app/models/pipeline_run.py:47`), causing the IntegrityError.

## Fix

Add `cascade="all, delete-orphan"` to the `PipelineStep.step_runs` relationship:

```python
step_runs = relationship("PipelineStepRun", back_populates="pipeline_step", cascade="all, delete-orphan")
```

This is consistent with existing relationships in the same codebase:
- `Pipeline.steps` — `cascade="all, delete-orphan"` (pipeline.py:20)
- `PipelineRun.step_runs` — `cascade="all, delete-orphan"` (pipeline_run.py:38)

## Affected Files

- `backend/app/models/pipeline.py` line 40 — add cascade to `PipelineStep.step_runs`

## Verification

- Deleting a pipeline step with existing `PipelineStepRun` records should succeed
- `PipelineStepRun` records referencing the deleted step should be removed
- Deleting a step with no runs should still work