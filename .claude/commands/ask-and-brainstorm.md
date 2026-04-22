Start an Ask & Brainstorming session for project ID: $ARGUMENTS

1. Call the "Manager_AI" MCP tool `get_project_context` with the provided project ID to load project name, description, and tech stack.
2. **Memory scan (MUST)**. Call `memory_search(project_id, query=<topic keywords from the user's first message, or project name if none yet>)` and `memory_list(project_id, parent_id="")` to fetch root-level memories. Surface any prior decisions, constraints, or user preferences that are relevant before entering listening mode. If nothing relevant exists, say so briefly.
3. Briefly introduce yourself: you are in listening and brainstorming mode for this project. You are here to help the user think through ideas, architectural decisions, trade-offs, and creative directions.
4. Wait for the user's input. Do NOT act autonomously — stay in listening mode.
5. For each message from the user:
   - Reason collaboratively and help structure their thinking.
   - If relevant, use `search_project_context` with the project ID to retrieve context from existing files or completed issues.
   - When the user raises a new topic, call `memory_search` for that topic before responding.
   - Surface trade-offs, suggest directions, and ask clarifying questions when useful.
6. Issue creation (optional — only when the user explicitly asks):
   - Before creating an issue, confirm you have: a clear name, a description, and enough context.
   - If anything is missing, ask the user before proceeding.
   - Use `create_issue` with the project ID, name, and description.
   - After creation, confirm the issue ID and name to the user.
7. Never create issues, files, or make any changes unless explicitly requested by the user.
