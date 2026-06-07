Fixed "Unknown" agent name in pipeline event rules display. Root cause: `EventRulesSection` used `agents.get(rule.source_step_id)` to find agent names, but `source_step_id` is a pipeline step ID — not an agent ID. The agents map (agent_id → name) never matched, so "Unknown" always rendered.

Added `ruleStepName(stepId, steps, agents)` helper that resolves: stepId → find step in steps array → step.agent_id → agents.get(agent_id). Applied to all 4 agent name lookups in EventRulesSection (existing rule display + Add Rule form dropdowns).

No memory write needed — the data model constraint (event rules store step IDs, not agent IDs) is enforced by the schema and the fix itself.