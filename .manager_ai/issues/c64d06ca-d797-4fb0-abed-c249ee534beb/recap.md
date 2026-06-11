Fixed 4 root causes that prevented auto-queue from starting issues:

1. **`_queue_add_direct` bypassed auto-start** — The fallback function created QueueEntry but never called `_maybe_auto_start_first`. Fixed by re-checking `issue_queue_service_ref` at function end and delegating auto-start if service is available and enabled.

2. **`load_state()` swallowed all exceptions silently** — Any error during startup (transient DB issue, misconfiguration) set `_enabled = False` with only a warning log. Fixed by splitting `KeyError` (expected, setting not found) from `Exception` (unexpected, now logged with full traceback).

3. **Ghost REASONING issues blocked queue forever** — If `run_issue()` failed after QueueEntry was DISPATCHING but issue stayed REASONING, all subsequent auto-starts were blocked. Added `_count_active_reasoning()` helper that checks QueueEntry status (only counts REASONING issues with PENDING or DISPATCHING QueueEntry as active). Applied to both `_maybe_auto_start_first` and `startup_resume`.

4. **Redundant fire-and-forget `create_task` in `add_to_queue()`** — Dual dispatch path (direct create_task + event-driven `_on_issue_queued`) was redundant and risky. Removed the create_task in favor of the event-driven path which reliably handles auto-start with proper error handling.

All changes in `backend/app/services/issue_queue_service.py`. 7 new tests added, 70 total pass.