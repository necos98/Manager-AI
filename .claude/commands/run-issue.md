Start working on the issue with ID: $ARGUMENTS

1. Call the "Manager_AI" MCP tool `get_issue_details` with the provided issue ID to fetch full issue information.
2. Based on the issue's current status, continue the pipeline:
   - **New / Declined**: Analyze the issue, set a name if missing. **You MUST invoke the `superpowers:brainstorming` skill** before writing the specification, then save the result via `create_issue_spec`. **Do NOT create local `.md` files** for the spec — always use the Manager AI MCP tools.
   - **Reasoning**: Review the spec. **You MUST invoke the `superpowers:writing-plans` skill** before creating the implementation plan, then save the result via `create_issue_plan` with atomic tasks (`create_plan_tasks`). **Do NOT create local `.md` files** for the plan — always use the Manager AI MCP tools.
   - **Planned**: Review the plan, accept it (`accept_issue`), and begin implementation.
   - **Accepted**: Pick up the next pending task, implement it, and update task statuses as you go. When all tasks are done, complete the issue (`complete_issue`).
3. Always fetch project context (`get_project_context`) before starting implementation to understand the codebase.
4. Work through tasks sequentially, updating each task status to "In Progress" when starting and "Completed" when done.
5. When all tasks are completed, write a recap and call `complete_issue`.
