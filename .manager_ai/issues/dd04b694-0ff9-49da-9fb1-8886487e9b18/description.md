## Pipeline agents' intents miss `finished_pipeline_step`  

### Summary  
Most pipeline agents' `intent` field does NOT mention calling `finished_pipeline_step` as the final action. While `run-pipeline.md` step 6 covers this generically, agents rely primarily on their intent (which is injected as a system instruction). When the intent doesn't mention step completion, agents may complete their work and exit without signaling the pipeline, causing the orchestrator to hang waiting for the `asyncio.Event`.

### Affected agents and their intents  
All agents checked (intent field does NOT say to call `finished_pipeline_step`):

| Agent | Intent says | Missing |
|-------|------------|---------|
| **SpecReviewer** | "review specs, apply fixes via edit_issue_spec, record in memory" | No mention of signalling completion |
| **SpecWriter** | "write spec, save via create_issue_spec, set name" | No mention of signalling completion |
| **PlanReviewer** | "review plan, fix via edit_issue_plan" | No mention of signalling completion |
| **PlanWriter** | "create plan + tasks, then call accept_issue" | No mention of `finished_pipeline_step` after `accept_issue` |
| **TaskWriter** | "break plan into atomic tasks" | No mention of signalling completion |
| **Developer** | "implement tasks, update status" | No mention of signalling completion |
| **CodeReviewer** | "review for bugs + security" | No mention of signalling completion |
| **QualityReviewer** | "review code quality + test coverage" | No mention of signalling completion |
| **Tester** | "run tests, then complete_issue" | No mention of `finished_pipeline_step` before `complete_issue` |
| **Closer** | "verify tasks, write recap, complete_issue" | No mention of `finished_pipeline_step` (has `allowed_tools: null` → all tools, but intent doesn't say to use it) |

### How the flow works (expected)  
`run-pipeline.md` step 6 says: "When your step is complete, call `finished_pipeline_step`". This instruction is part of the slash command loaded when claude runs `/run-pipeline {issue_id}`. The agent reads it alongside its intent.

### How it breaks  
The intent is more specific and authoritative than the generic step 6. Claude models prioritize specific instructions over general ones. When the intent says "do X, then Y, then Z" and Z is the last step, the model may consider the task done after Z and skip `finished_pipeline_step`.  

Log evidence: no `"Step X completed"` events, pipeline stays in RUNNING status with `current_step_index` unchanged, eventual timeout after 1800s with: `"Step X timed out after 1800s"`.

### Fix  
Append `"When all your work is done, call finished_pipeline_step to signal completion."` to EVERY agent's intent field. This ensures the instruction is in the agent's primary instruction set, not just the generic slash command page.

For agents that already have a terminal action (PlanWriter: `accept_issue`, Tester: `complete_issue`), the intent must explicitly sequence them:
- PlanWriter: "...then call accept_issue to accept the plan, then call finished_pipeline_step to signal the pipeline to advance."
- Tester: "...then call complete_issue to finalize, then call finished_pipeline_step."

### Impact  
All pipelines, all platforms. Probabilistic — depends on whether the Claude model follows intent over generic instructions. More likely with complex intents (more steps = higher chance of forgetting final step).