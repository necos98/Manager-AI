## Bug

Pipeline event rules display "Unknown" instead of the agent name when viewing rules in the Pipelines tab.

## Root Cause

In `EventRulesSection` component (`PipelinesTab.tsx`), the code does `agents.get(rule.source_step_id)` to look up agent names. The `agents` map is keyed by `agent_id`, but `source_step_id` is a **pipeline step ID** — not an agent ID. The lookup always returns `undefined`, and the fallback `"Unknown"` is shown.

## Fix

Add a helper `ruleStepName(stepId, steps, agents)` that resolves a step ID to the step's `agent_id`, then looks up the agent name:

1. Find step by `stepId` in the `steps` array
2. Get `step.agent_id` from the matched step
3. Look up `agents.get(step.agent_id)`

Apply this helper to both existing rule display and the Add Rule form dropdowns.

## Files Changed

- `frontend/src/features/pipelines/components/PipelinesTab.tsx` — new `ruleStepName()` function, 4x `agents.get(rule.*_step_id)` → `ruleStepName(...)`, 2x `agents.get(s.agent_id)` → `ruleStepName(...)`