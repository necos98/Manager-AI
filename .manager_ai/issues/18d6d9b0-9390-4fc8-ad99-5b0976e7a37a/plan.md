## Implementation Plan

Single-route fix in `backend/app/routers/pipelines.py`.

### Task 1: Reorder update_pipeline route

**Files:** Modify `backend/app/routers/pipelines.py:67-77`

Swap the order of `_response()` and `await db.commit()`, and re-fetch the pipeline after commit to get fresh server-side defaults. Match the `create_pipeline` pattern.

```python
@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: str,
    data: PipelineUpdate,
    db: AsyncSession = Depends(get_db),
):
    svc = PipelineService(db)
    await svc.update_pipeline(pipeline_id, data.name)
    await db.commit()
    return _response(await svc.get_pipeline(pipeline_id))
```

### Task 2: Run tests

Run `python -m pytest tests/ -k "pipeline" -v` to verify 17/17 pass and no regression.