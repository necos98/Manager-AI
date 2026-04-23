Start working on the issue with ID: $ARGUMENTS

1. Call the "Manager_AI" MCP tool `get_issue_details` with the provided issue ID and project_id that you can find in the file "manager.json" in the root of the project to fetch full issue information.
2. **Memory read (MUST)**. Run `Grep -ri "<3–5 keywords from issue description>" .manager_ai/memories/` on the project root. If there are hits, `Read` the relevant `.manager_ai/memories/<id>.md` files and factor them into spec/plan/implementation. Skip only for trivial issues (typo fix, rename).
3. Based on the issue's current status, continue the pipeline:
   - **New / Declined**: Analyze the issue, set a name if missing. **You MUST invoke the `superpowers:brainstorming` skill** before writing the specification, then save the result via `create_issue_spec`. **Do NOT create local `.md` files** for the spec — always use the Manager AI MCP tools.
   - **Reasoning**: Review the spec. **You MUST invoke the `superpowers:writing-plans` skill** before creating the implementation plan, then save the result via `create_issue_plan` with atomic tasks (`create_plan_tasks`). **Do NOT create local `.md` files** for the plan — always use the Manager AI MCP tools.
   - **Planned**: Review the plan, accept it (`accept_issue`), and begin implementation.
   - **Accepted**: Pick up the next pending task, implement it, and update task statuses as you go. When all tasks are done, complete the issue (`complete_issue`).
4. Always fetch project context (`get_project_context`) before starting implementation to understand the codebase.
5. Work through tasks sequentially, updating each task status to "In Progress" when starting and "Completed" when done.
6. When all tasks are completed, write a recap and call `complete_issue`. Then: **Memory write (MUST)**. From the recap, extract durable facts — decisions with reasoning, constraints not enforced by code, user preferences revealed, non-obvious gotchas. For each fact, `Grep -ri "<keyword>" .manager_ai/memories/` first to check for an existing memory; then `memory_update` it if found, or `memory_create` a new one. Do not save transient task state, spec/plan summaries (already in the issue record), or info already in `CLAUDE.md`.
