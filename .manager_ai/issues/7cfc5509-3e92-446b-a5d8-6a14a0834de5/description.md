Pipeline system database schema and SQLAlchemy models.

**Tables needed:**

1. **agents** — agent definition (reusable across pipelines)
   - id (UUID, PK)
   - project_id (FK → projects)
   - name (string, unique per project)
   - system_prompt (text)
   - model (string, optional — e.g. "opus", "sonnet")
   - allowed_tools (JSON list, optional — e.g. ["mcp__ManagerAi__get_issue_details", "mcp__ManagerAi__create_issue_spec"])
   - created_at, updated_at

2. **pipelines** — ordered list of steps linking to agents
   - id (UUID, PK)
   - project_id (FK → projects)
   - name (string)
   - created_at, updated_at

3. **pipeline_steps** — each step in a pipeline (ordered)
   - id (UUID, PK)
   - pipeline_id (FK → pipelines)
   - agent_id (FK → agents)
   - order_index (integer)
   - terminal_command (string — the command to run, e.g. `claude "/run-pipeline-step $STEP_ID" --dangerously-skip-permissions`)

4. **pipeline_runs** — a pipeline execution for an issue
   - id (UUID, PK)
   - pipeline_id (FK → pipelines)
   - issue_id (string)
   - status (enum: RUNNING, COMPLETED, FAILED)
   - current_step_index (integer)
   - started_at, finished_at
   - created_at

5. **pipeline_step_runs** — individual step execution
   - id (UUID, PK)
   - pipeline_run_id (FK → pipeline_runs)
   - pipeline_step_id (FK → pipeline_steps)
   - terminal_id (FK → terminal_commands, nullable)
   - status (enum: PENDING, RUNNING, COMPLETED, FAILED)
   - started_at, finished_at

6. **pipeline_messages** — inter-agent chat messages
   - id (UUID, PK)
   - pipeline_run_id (FK → pipeline_runs)
   - sender_agent_name (string)
   - content (text, markdown)
   - created_at

**Deliverables:**
- SQLAlchemy models for all 6 tables
- Alembic migration
- Unit test: verify table creation + relationships