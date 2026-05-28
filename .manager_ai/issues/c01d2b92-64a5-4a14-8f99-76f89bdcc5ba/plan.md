## Fix

Add `cascade="all, delete-orphan"` to `Pipeline.runs` relationship.

**File:** `backend/app/models/pipeline.py:21`

**Change:**
```python
# Before
runs = relationship("PipelineRun", back_populates="pipeline")

# After
runs = relationship("PipelineRun", back_populates="pipeline", cascade="all, delete-orphan")
```

## Validation

1. Start backend: `python start.py`
2. Create a pipeline, run it at least once (creates PipelineRun records)
3. Delete the pipeline via API: `DELETE /api/projects/{project_id}/pipelines/{pipeline_id}`
4. Verify: 200 OK (not 500), pipeline and all runs deleted from DB

## Notes

- No migration needed (relationship-level change, no schema change)
- `PipelineRun.step_runs` and `PipelineRun.messages` already have cascade configured — delete chains correctly
- Same fix pattern as memory `6e2ccbe6` (PipelineStep.step_runs cascade fix)