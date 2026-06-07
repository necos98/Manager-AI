Removed issue lifecycle state transitions from 4 pipeline agent intents to eliminate conflict with `/run-pipeline` step 6.

**Changes:**
- **PlanWriter**: removed `accept_issue` from intent. Intent now ends at "record non-obvious architectural decisions in memory."
- **Closer**: removed step 5 (call `complete_issue`). Renumbered, rephrased opening from "finalize and complete issues" to "verify and finalize issues."
- **Tester**: removed `complete_issue` from step 5, rephrased opening from "test code and close issues" to "test code and report results."
- **CodeReviewer**: removed "Do NOT call complete_issue unless you are the final pipeline step."

**No code changes**: `DEFAULT_AGENTS` in agent_service.py were already clean. All updates were MCP `update_agent` calls on existing DB agents.

**Design decision**: lifecycle instructions (`accept_issue`, `complete_issue`, `finished_pipeline_step`) live exclusively in `/run-pipeline` command. Intents only describe domain-specific work. This prevents Claude models from treating the intent's terminal action as the end of work and skipping `finished_pipeline_step`, which caused 1800s pipeline timeouts.