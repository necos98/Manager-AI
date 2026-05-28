Work on issue $ARGUMENTS as part of a pipeline workflow.

1. Call the "Manager_AI" MCP tool `get_active_agent` with the provided issue ID to discover which agent role you are playing (e.g. "SpecWriter", "Developer", "Reviewer").

2. Call `get_active_pipeline_run` with the issue ID to see the full pipeline — which steps have completed, which are pending, and your current position.

3. Call `get_issue_details` to get the full issue information. You can find the project_id in the file "manager.json" at the project root.

4. Based on your agent role, perform the appropriate work:

   - **BrainstormingAgent**: Analyze the issue from scratch. Set a name if missing via `set_issue_name`. Then **invoke the `superpowers:brainstorming` skill**, produce a design/spec, and save it via `create_issue_spec`. Finally, create the implementation plan via `create_issue_plan` with atomic tasks via `create_plan_tasks`.

   - **CodebaseExplorer**: Explore the codebase to understand the context of this issue. Trace relevant code paths, identify files that need changes, patterns to follow, and dependencies to consider. Document your findings. Do NOT modify any files — this is analysis only.

   - **SpecWriter**: Write a detailed specification for the issue. **Invoke the `superpowers:brainstorming` skill** before writing, then save via `create_issue_spec`. Cover architecture, components, data flow, error handling, and testing.

   - **PlanWriter**: Create an implementation plan from the specification. Break the design into atomic, ordered tasks with specific files to create or modify. Save via `create_issue_plan` and `create_plan_tasks`.

   - **Developer**: Implement the code changes described in the plan. Work through tasks sequentially: update each to "In Progress" when starting, "Completed" when done. Follow existing codebase patterns and conventions. Make autonomous decisions — do NOT ask for confirmations. If you hit a genuine blocker, use `ask_user_question`.

   - **Reviewer**: Review the code changes made by the Developer. Check for bugs, logic errors, security vulnerabilities, code quality issues, and adherence to project conventions. Report findings.

   - **QA / Tester**: If you are a QA agent, run tests, verify behavior, and report any issues.

5. **Memory protocol** — before making architectural decisions, `Grep -ri "<keywords>" .manager_ai/memories/`. After completing your work, save durable facts via `memory_create` or `memory_update`.

6. When your step is complete, type `exit` to allow the pipeline to advance to the next agent. The next agent will then take over automatically.
