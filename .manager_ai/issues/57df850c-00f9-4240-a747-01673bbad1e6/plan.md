# Implementation Plan: Fix UNIQUE constraint violation on pipeline step reorder

## Files

- **Modify:** `backend/app/services/pipeline_service.py:109-126` — `reorder_steps` method

## Tasks

### Task 1: Wrap reorder_steps in no_autoflush block

**File:** `backend/app/services/pipeline_service.py`

- [ ] Add `async with self.session.no_autoflush:` context manager around the loop body (lines 111-125)
- [ ] Keep the explicit `await self.session.flush()` at the end inside the block
- [ ] Run existing pipeline tests to verify no regressions

### Task 2: Add test for step reorder

**File:** `backend/tests/test_services_pipeline.py` (or appropriate test file)

- [ ] Write test that creates pipeline with 3 steps, reorders them in reverse, verifies new order_index values
- [ ] Write test that reproduces the original bug (reorder triggers autoflush conflict), verifies it passes with fix
- [ ] Run tests, verify all pass

## Implementation Detail

Current code (lines 109-126):
```python
async def reorder_steps(
    self, pipeline_id: str, step_ids: list[str]
) -> list[PipelineStep]:
    steps = []
    for i, step_id in enumerate(step_ids):
        result = await self.session.execute(
            select(PipelineStep).where(
                PipelineStep.id == step_id,
                PipelineStep.pipeline_id == pipeline_id,
            )
        )
        step = result.scalar_one_or_none()
        if step is None:
            raise NotFoundError(f"Pipeline step not found: {step_id}")
        step.order_index = i
        steps.append(step)
    await self.session.flush()
    return steps
```

Fixed code:
```python
async def reorder_steps(
    self, pipeline_id: str, step_ids: list[str]
) -> list[PipelineStep]:
    async with self.session.no_autoflush:
        steps = []
        for i, step_id in enumerate(step_ids):
            result = await self.session.execute(
                select(PipelineStep).where(
                    PipelineStep.id == step_id,
                    PipelineStep.pipeline_id == pipeline_id,
                )
            )
            step = result.scalar_one_or_none()
            if step is None:
                raise NotFoundError(f"Pipeline step not found: {step_id}")
            step.order_index = i
            steps.append(step)
        await self.session.flush()
    return steps
```

The `no_autoflush` context manager prevents SQLAlchemy from flushing dirty state during query execution inside the loop. All `order_index` values are assigned in memory, then the explicit `flush()` writes them all at once — no temporary constraint conflict.