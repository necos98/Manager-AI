## PlanWriter intent: `accept_issue` without `finished_pipeline_step` causes pipeline stall  

### Summary  
PlanWriter's `intent` field explicitly instructs the agent to call `accept_issue` as its final step:

> "After writing the plan, record non-obvious architectural decisions in memory, then call accept_issue to move the issue to Accepted so downstream agents can begin implementation."

This is the **only** agent intent that includes a terminal MCP tool call (`accept_issue`). The problem: `accept_issue` changes the issue status to ACCEPTED but does NOT signal pipeline step completion. The agent does its work, calls `accept_issue`, and then — following its intent literally — considers itself done. It never calls `finished_pipeline_step`.

Meanwhile, `_execute()` in `pipeline_run_service.py` is blocked in `_run_step()` waiting for the `asyncio.Event` that only `finished_pipeline_step` triggers. The pipeline is stuck in RUNNING status with `current_step_index` pointing to PlanWriter indefinitely (until 1800s timeout).

### Downstream consequence  
Even if the pipeline eventually times out and fails, the issue is now in ACCEPTED status. A failed pipeline run + ACCEPTED issue = inconsistent state. The user sees:
- Pipeline run: FAILED (timeout)  
- Issue: ACCEPTED (ready for implementation)  
- No automated handoff happens

### Root cause  
The PlanWriter intent treats `accept_issue` as the terminal action. But in pipeline context, `accept_issue` is just a state transition — it doesn't interact with the pipeline mechanism at all. The pipeline's step completion mechanism (`finished_pipeline_step`) is orthogonal to issue status.

This is unique to PlanWriter. Other agents' intents end with passive statements ("report findings", "record in memory") which don't satisfy the agent's sense of completion, making them more likely to fall through to `run-pipeline.md` step 6. PlanWriter's intent ends with an explicit MCP call, which strongly signals "this is the last thing to do."

### Fix  

**Immediate fix — PlanWriter intent:**
Append `"After calling accept_issue, call finished_pipeline_step with a handoff summary for the next agent."` to the PlanWriter intent in the DB and in `agent_service.py:DEFAULT_AGENTS`.

**Defensive fix — pipeline orchestrator:**
In `finished_pipeline_step`, if no active pipeline run is found (line 1279-1280), check if the issue just transitioned to ACCEPTED and create a synthetic completion signal. This is not ideal (masking the bug) but prevents silent stalls.

### Detection  
Pipeline run stuck at PlanWriter step:
1. Pipeline UI shows PlanWriter as current step, status RUNNING
2. Issue status shows ACCEPTED
3. No `"agent_step_completed"` event for PlanWriter
4. After 1800s: `"Step PlanWriter timed out after 1800s"` in logs
5. Pipeline run transitions to FAILED

### Impact  
Medium. Only affects PlanWriter step. Only when the PlanWriter's intent includes `accept_issue` (current state). Probabilistic — depends on whether Claude treats the intent as exhaustive.