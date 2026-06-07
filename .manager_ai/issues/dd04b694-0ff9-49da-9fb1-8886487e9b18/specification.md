## Remove lifecycle state transitions from pipeline agent intents

### Problem
Pipeline agent intents contain issue lifecycle state transitions (`accept_issue`, `complete_issue`) that conflict with `/run-pipeline` step 6 ("call `finished_pipeline_step`"). Claude models prioritize the more specific intent instructions, so they complete the final intent step and exit without signaling the pipeline orchestrator, causing 1800s timeouts.

### Solution
Remove ALL issue lifecycle state transitions from agent intents. The `/run-pipeline` command remains the single source of truth for lifecycle management (step 6: "call `finished_pipeline_step`"). Intents should only describe domain-specific work, not how to signal completion.

### Affected agents
Four DB agents currently reference lifecycle transitions:

1. **PlanWriter** — has `accept_issue` in intent
2. **Closer** — has `complete_issue` in intent
3. **Tester** — has `complete_issue` in intent
4. **CodeReviewer** — references `complete_issue` in intent

### Non-goals
- No changes to `/run-pipeline` command or orchestrator logic
- No new safety nets or fallback mechanisms
- DEFAULT_AGENTS in agent_service.py are already clean — no code changes needed
- No changes to agents that already have clean intents (BrainstormAgent, BugHunter, Developer, PlanReviewer, QualityReviewer, SpecReviewer, SpecWriter, TaskWriter)

### Acceptance criteria
- PlanWriter intent no longer mentions `accept_issue`
- Closer intent no longer mentions `complete_issue`
- Tester intent no longer mentions `complete_issue`
- CodeReviewer intent no longer references `complete_issue`
- All lifecycle instructions stay exclusively in `/run-pipeline` command
