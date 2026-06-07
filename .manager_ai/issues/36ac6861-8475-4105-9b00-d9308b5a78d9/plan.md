## Implementation Plan: Refactor PipelineRunService._execute()

**File:** `backend/app/services/pipeline_run_service.py`
**Target:** `_execute()` method (lines 245-454, ~210 lines)

Extract into 5 private methods. Preserve all behavior, constraints, and test compatibility.

---

### Method 1: `_wait_for_run(run_id, session)`

**Lines to extract:** 252-276 (retry loop + fetch pipeline + get sorted steps)

**Signature:**
```python
async def _wait_for_run(
    self, run_id: str, session: AsyncSession
) -> tuple[PipelineRun, list[PipelineStep]]:
```

**Return:** `(run, steps)` — where `steps` is `sorted(pipeline.steps, key=lambda s: s.order_index)`

**Behavior:**
- Retry loop: 50 iterations × 100ms sleep, calls `self._get_run_with_session(run_id, session)`
- If run never found after loop: log error, return `(None, None)` (preserves current early-return behavior)
- Fetch pipeline via `select(Pipeline).where(Pipeline.id == run.pipeline_id)` with `selectinload(Pipeline.steps).selectinload(PipelineStep.agent)`
- If pipeline not found: return `(None, None)`
- Sort steps by `order_index`, return `(run, steps)`

**Callers:** Called once at top of `_execute()`

**Test notes:** Private method. No direct test needed — covered by existing `_execute()` tests.

---

### Method 2: `_setup_step_environment(step, run, session, project_id, project_path)`

**Lines to extract:** 282-349 (fetch step_run → mark RUNNING → create terminal → WSL cd → emit events)

**Signature:**
```python
async def _setup_step_environment(
    self,
    step: PipelineStep,
    run: PipelineRun,
    session: AsyncSession,
    project_id: str,
    project_path: str,
) -> tuple[str, str, PipelineStepRun, PipelineStep]:
```

**Return:** `(term_id, agent_name, step_run, step)`

**Behavior (preserved exactly):**
1. Fetch latest `PipelineStepRun` for `(run_id, pipeline_step_id=step.id)` via `scalars().first()` with `ORDER BY started_at DESC NULLS LAST` (constraint: rejection creates duplicate rows)
2. If `step_run is None`: `continue` (skips iteration)
3. Set `step_run.status = RUNNING`, `step_run.started_at = now`, update `run.current_step_index = i`, flush
4. Get `agent_name` and `agent.intent` from `step.agent`
5. Fetch `Project.shell` and `Project.wsl_distro` via `session.get(Project, project_id)`
6. Create terminal via `terminal_service.create(...)` with shell and wsl_distro passed through
7. Set `step_run.terminal_id = term_id`, commit
8. If WSL shell: emit `cd <posix_path>\r\n` into PTY
9. Emit `agent_step_started` event
10. Emit `terminal_created` event

**Imports kept inline:** `from app.models.project import Project`, `from app.services.wsl_support import is_wsl_shell, win_to_wsl_path`

**Callers:** Called once per iteration of the while loop in `_execute()`, just before the try/except/finally block.

---

### Method 3: `_handle_step_completion(run, step_run, session, success, agent_name, project_id, issue_id)`

**Lines to extract:** 370-395 (success/failure routing + commit + event emission)

**Signature:**
```python
async def _handle_step_completion(
    self,
    run: PipelineRun,
    step_run: PipelineStepRun,
    session: AsyncSession,
    success: bool,
    agent_name: str,
    project_id: str,
    issue_id: str,
) -> bool:
```

**Return:** `True` if loop should continue, `False` if loop should break (failure).

**Behavior:**
- If `success is True`:
  - Set `step_run.status = COMPLETED`
  - Increment `run.current_step_index += 1`
  - Emit `agent_step_completed` event
  - Return `True`
- If `success is False`:
  - Set `step_run.status = FAILED`, `run.status = FAILED`
  - Set `step_run.finished_at = now`
  - Commit via `_safe_commit_session`
  - Emit `agent_step_failed` event
  - Return `False`

**Note:** `step_run.finished_at = now` for the success case is set AFTER this method returns (line 394), as is `_safe_commit_session`. Keep that in `_execute()`.

**Callers:** Called inside the try block of the per-step loop in `_execute()`, after the REJECTED check.

---

### Method 4: `_cleanup_step(term_id)`

**Lines to extract:** 412-416 (finally block — save recording, stop reader, pop session, kill terminal)

**Signature:**
```python
async def _cleanup_step(self, term_id: str) -> None:
```

**Behavior (preserved exactly — order is critical):**
1. `_save_recording(term_id, terminal_service.get_buffered_output(term_id))`
2. `_stop_reader(term_id)`
3. `_sessions.pop(term_id, None)`
4. `terminal_service.kill(term_id)`

**Constraint:** This exact order is a historical fix. Do NOT reorder. See memory `a17aafc9`.

**Callers:** Called in the `finally` block of each per-step iteration.

---

### Method 5: `_finalize_run(run, session, project_id, issue_id, run_id)`

**Lines to extract:** 418-430 (set COMPLETED, commit, emit pipeline_completed)

**Signature:**
```python
async def _finalize_run(
    self,
    run: PipelineRun,
    session: AsyncSession,
    project_id: str,
    issue_id: str,
    run_id: str,
) -> None:
```

**Behavior:**
1. `await session.refresh(run)`
2. If `run.status != FAILED`: set `run.status = COMPLETED`
3. Set `run.finished_at = now`
4. `await self._safe_commit_session(session)`
5. Emit `pipeline_completed` event with current `run.status.value`

**Callers:** Called after the while loop in the happy path. **Not** called from the outer exception handler — that handler sets FAILED and emits pipeline_completed inline (lines 433-447), keeping the fallback explicit for robustness.

---

### Changes to `_execute()` body after extraction

Lines 245-454 become:

```python
async def _execute(
    self, run_id: str, project_id: str, project_path: str
) -> None:
    session = self.session
    if self.session_factory is not None:
        session = self.session_factory()

    try:
        run, steps = await self._wait_for_run(run_id, session)
        if run is None:
            return

        while run.current_step_index < len(steps) and run.status != PipelineRunStatus.FAILED:
            i = run.current_step_index
            step = steps[i]

            term_id, agent_name, step_run, step = await self._setup_step_environment(
                step, run, session, project_id, project_path
            )
            if step_run is None:
                continue

            try:
                success = await self._run_step(
                    term_id=term_id,
                    agent_name=agent_name,
                    intent=step.agent.intent if step.agent else "",
                    issue_id=run.issue_id,
                    run_id=run_id,
                    step_index=i,
                )

                # Refresh to pick up rejection changes from reject_step()
                await session.refresh(run)
                await session.refresh(step_run)

                if step_run.status == PipelineStepRunStatus.REJECTED:
                    step_run.finished_at = datetime.now(timezone.utc)
                    await self._safe_commit_session(session)
                    continue

                should_continue = await self._handle_step_completion(
                    run, step_run, session, success, agent_name,
                    project_id, run.issue_id,
                )
                if not should_continue:
                    break

                step_run.finished_at = datetime.now(timezone.utc)
                await self._safe_commit_session(session)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Step %s failed with exception", agent_name)
                step_run.status = PipelineStepRunStatus.FAILED
                run.status = PipelineRunStatus.FAILED
                step_run.finished_at = datetime.now(timezone.utc)
                await self._safe_commit_session(session)
                await event_service.emit({
                    "type": "agent_step_failed",
                    "project_id": project_id,
                    "issue_id": run.issue_id,
                    "agent_name": agent_name,
                    "step_run_id": step_run.id,
                })
                break
            finally:
                await self._cleanup_step(term_id)

        await self._finalize_run(run, session, project_id, run.issue_id, run_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Pipeline %s failed with unexpected error", run_id)
        try:
            run.status = PipelineRunStatus.FAILED
            run.finished_at = datetime.now(timezone.utc)
            await self._safe_commit_session(session)
        except Exception:
            pass
        await event_service.emit({
            "type": "pipeline_completed",
            "project_id": project_id,
            "issue_id": run.issue_id,
            "run_id": run_id,
            "status": PipelineRunStatus.FAILED.value,
        })
    finally:
        if self.session_factory is not None:
            try:
                await session.close()
            except Exception:
                pass
        await pipeline_task_manager.cleanup_task(run_id)
```

---

### Key constraints to preserve

1. **Step_run ordering:** `scalars().first()` + `ORDER BY started_at DESC NULLS LAST` — rejection creates duplicates
2. **Session factory pattern:** Prod uses `self.session_factory()`, tests inject shared session. All extracted methods receive session as parameter.
3. **WSL cd order:** After terminal creation, before `_run_step()`
4. **Cleanup order:** `_save_recording` → `_stop_reader` → `_sessions.pop` → `terminal_service.kill`
5. **REJECTED detection:** `session.refresh()` after `_run_step()` to pick up concurrent `reject_step()` changes
6. **CancelledError propagates** — never caught
7. **Outer exception handler** stays inline — sets FAILED + emits pipeline_completed as fallback
8. **while-loop structure** preserved — driven by `run.current_step_index`
9. **Late imports** (Project model, wsl_support) remain inside `_setup_step_environment`, not hoisted

---

### No changes outside this file

Per spec non-goals: no changes to models, schemas, frontend, tests, or other services.
