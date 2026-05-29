# Fix: Pipeline add_step UNIQUE constraint on order_index

## Files
- **Modify:** `backend/app/services/pipeline_service.py:81-96` — `add_step` method
- **Modify:** `backend/tests/test_models_pipeline.py` — add test for auto-index behavior

## Task 1: Write failing test

Add to `backend/tests/test_models_pipeline.py`:

```python
@pytest.mark.asyncio
async def test_add_step_auto_assigns_next_order_index(db_session):
    """Adding a step auto-assigns max+1 instead of using the passed order_index."""
    from app.services.pipeline_service import PipelineService

    agent = Agent(id="a1", name="dev", system_prompt="Dev")
    pipeline = Pipeline(id="pl1", name="Test")
    db_session.add_all([agent, pipeline])
    await db_session.flush()

    svc = PipelineService(db_session)

    # First step: passed order_index=0, gets 0
    step1 = await svc.add_step("pl1", "a1", order_index=0, terminal_command="cmd1")
    assert step1.order_index == 0

    # Second step: passed order_index=0, but auto-assigned 1 (max+1)
    step2 = await svc.add_step("pl1", "a1", order_index=0, terminal_command="cmd2")
    assert step2.order_index == 1

    # Third step: auto-assigned 2
    step3 = await svc.add_step("pl1", "a1", order_index=0, terminal_command="cmd3")
    assert step3.order_index == 2
```

Run: `python -m pytest backend/tests/test_models_pipeline.py::test_add_step_auto_assigns_next_order_index -v`

Expected: FAIL — IntegrityError on second add_step.

## Task 2: Fix add_step

In `backend/app/services/pipeline_service.py`, change `add_step` to query max order_index first:

```python
async def add_step(
    self,
    pipeline_id: str,
    agent_id: str,
    order_index: int,
    terminal_command: str = "",
) -> PipelineStep:
    # Auto-assign next available index
    from sqlalchemy import func
    result = await self.session.execute(
        select(func.max(PipelineStep.order_index)).where(
            PipelineStep.pipeline_id == pipeline_id
        )
    )
    max_idx = result.scalar()
    next_idx = (max_idx + 1) if max_idx is not None else 0

    step = PipelineStep(
        pipeline_id=pipeline_id,
        agent_id=agent_id,
        order_index=next_idx,
        terminal_command=terminal_command,
    )
    self.session.add(step)
    await self.session.flush()
    return step
```

## Task 3: Run tests

Run: `python -m pytest backend/tests/test_models_pipeline.py -v`

Expected: All tests pass, including new `test_add_step_auto_assigns_next_order_index`.