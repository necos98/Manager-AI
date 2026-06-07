## Plan: Fix "Unknown" agent name in pipeline event rules

### Root Cause
`EventRulesSection` in `PipelinesTab.tsx` uses `agents.get(rule.source_step_id)` — but `source_step_id` is a pipeline step ID, not an agent ID. The `agents` map (agent_id → name) never matches, so fallback "Unknown" always renders.

### Fix
Add `ruleStepName(stepId, steps, agents)` helper that: stepId → find step → step.agent_id → agents.get(). Apply to all 4 name lookups in EventRulesSection.

### Task 1: Add helper and fix lookups

**File:** Modify `frontend/src/features/pipelines/components/PipelinesTab.tsx`

- [ ] Add `ruleStepName()` helper function
- [ ] Replace `agents.get(rule.source_step_id)` with `ruleStepName(rule.source_step_id, steps, agents)`
- [ ] Replace `agents.get(rule.target_step_id)` with `ruleStepName(rule.target_step_id, steps, agents)`
- [ ] Replace `agents.get(s.agent_id)` in Add Rule dropdowns with `ruleStepName(s.id, steps, agents)`

### Verification
- View a pipeline with event rules → agent names display correctly
- If no event rules → empty state unchanged